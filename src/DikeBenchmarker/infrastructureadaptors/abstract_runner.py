"""Adaptor to execution environment (cluster, SLURM, K8s, cloud API, vendor queue)."""

from abc import ABC, abstractmethod
import logging
import os
import time

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from DikeBenchmarker.benchmarkingmethods.benchmarker import AbstractBenchmarker

from DikeBenchmarker.benchmarkadaptors.abstractinstance import AbstractInstanceAdaptor
from DikeBenchmarker.solveradaptors.abstractexecutable import AbstractExecutable
from DikeBenchmarker.benchmarkatoms import Job, JobState, Result
from DikeBenchmarker.infrastructureadaptors.util import control


logger = logging.getLogger(__name__)

__all__ = ["AbstractRunner"]

FINISHED_STATES = {JobState.CANCELLED, JobState.FAILED, JobState.FINISHED}


class AbstractRunner(ABC):
    """Interface for Runners."""

    def __init__(self, solver_adaptor: AbstractExecutable = None, instance_adaptor: AbstractInstanceAdaptor = None):
        """Initialize the runner with the given adaptors."""
        self.jobs = list[Job]()
        self.instance_adaptor = instance_adaptor
        self.solver_adaptor = solver_adaptor

    def run(self, benchmarkers: list["AbstractBenchmarker"], njobs: int = 1):
        """Maintains the benchmarking process and blocks until benchmarking is finished (i.e., all jobs are completed).

        Also blocks until all consumers are finished.
        """
        logger.debug(f"Starting runner with {len(benchmarkers)} benchmarkers and a total of {njobs} jobs to submit.")

        i = j = 0
        # submit njobs to the runner
        while j < njobs and i < len(benchmarkers):
            job = benchmarkers[i].next_job()
            if job is None:
                i = i + 1
            elif self.submit(job):
                j = j + 1

        # iterate over the results
        for result in self.completions():
            logger.debug(f"Received result for job: Solver {result.get_job().solver_id} on Benchmark {result.get_job().benchmark_id}")
            if result.execution.has_error:
                if "loss of manager" in result.execution.get_detail:
                    # resubmit failed job if the error is due to loss of manager
                    self.submit(result.get_job().clone_retry())
                else:
                    logger.error(result.execution.get_detail)
                continue

            result.get_job().job_producer.handle_result(result)
            result.get_job().job_producer.results_to_consume.put(result)

            # submit the next job
            job = None
            while job is None and i < len(benchmarkers):
                job = benchmarkers[i].next_job()
                if job is None:
                    i = i + 1
                elif not self.submit(job):
                    job = None  # job rejected, try next job

        # signal the consumer thread of each benchmarker to finish and wait for it
        for benchmarker in benchmarkers:
            benchmarker.results_to_consume.put(None)
        for benchmarker in benchmarkers:
            benchmarker.result_consumer_thread.join()

        # tear down the external execution backend so it does not leave
        # orphaned resources (e.g. parsl worker blocks) behind on normal exit.
        self.teardown()

    def teardown(self):
        """Release any external resources held by the runner.

        Default implementation is a no-op; backends that allocate external
        resources (e.g. SLURM worker blocks) should override this.
        """

    @abstractmethod
    def submit(self, job: Job) -> bool:
        """Submit a job to the external system."""
        logger.debug(f"Submitting job: Solver {job.solver_id} on Benchmark {job.benchmark_id}")

        output_root = job.get_log_prefix()
        os.makedirs(os.path.dirname(output_root), exist_ok=True)
        if os.path.exists(f"{output_root}.done"):
            # if the .done file exists, the job was completed in a previous run; skip it
            # entirely. It must not be tracked in self.jobs, otherwise it would sit in a
            # non-terminal SUBMITTED state and block the completion loop until walltime.
            print(f"Job {job.solver_id} on {job.benchmark_id} already completed in previous run, skipping submission.")
            return False

        self.jobs.append(job)
        job.mark_submitted()
        return True

    @abstractmethod
    def completed(self, job: Job) -> Result:
        """If the job has completed.

        - update the job's state to either FINISHED or FAILED.
        - return a Result object or None.
        """

    def completions(self, sleep_duration: float = 1):
        """Yield whenever the external system reports a job as done/failed.

        Stops when all jobs are either CANCELLED, FAILED or FINISHED.

        Args:
            sleep_duration (float, optional): sleep duration in s between two polls of completed jobs. Defaults to 1.
        """
        while not all(j.state in FINISHED_STATES for j in self.jobs):
            for job in self.jobs:
                if control.is_shutting_down():
                    print("Runner is shutting down, cancelling job.")
                    self.cancel(job)
                    continue
                if job.state == JobState.RUNNING:
                    result = self.completed(job)
                    if result is not None:
                        yield result
                time.sleep(sleep_duration)
            if control.is_shutting_down():
                print("Runner is shutting down, exiting completions loop.")
                return
        # all jobs reached a finished state without an external shutdown:
        # signal that no requeue/continuation is needed.
        control.flag_all_jobs_complete()

    @abstractmethod
    def cancel(self, job: Job):
        """Best-effort cancellation if supported by the external system."""
        job.cancel_local()

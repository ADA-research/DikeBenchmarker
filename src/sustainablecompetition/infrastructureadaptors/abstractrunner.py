"""
Adaptor to execution environment (cluster, SLURM, K8s, cloud API, vendor queue).
"""

from abc import ABC, abstractmethod
import logging
import time

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sustainablecompetition.benchmarkingmethods.abstract_benchmarker import AbstractBenchmarker

from sustainablecompetition.benchmarkadaptors.abstractinstance import AbstractInstanceAdaptor
from sustainablecompetition.solveradaptors.abstractexecutable import AbstractExecutable
from sustainablecompetition.benchmarkatoms import Job, JobState, Result


logger = logging.getLogger(__name__)

__all__ = ["AbstractRunner"]

FINISHED_STATES = {JobState.CANCELLED, JobState.FAILED, JobState.FINISHED}


class AbstractRunner(ABC):
    """Interface for Runners"""

    def __init__(self, solver_adaptor: AbstractExecutable = None, instance_adaptor: AbstractInstanceAdaptor = None):
        self.jobs = list[Job]()
        self.instance_adaptor = instance_adaptor
        self.solver_adaptor = solver_adaptor

    def run(self, benchmarkers: list["AbstractBenchmarker"], njobs: int = 1):
        """
        Maintains the benchmarking process and blocks until benchmarking is finished (i.e., all jobs are completed).
        Also blocks until all consumers are finished.
        """
        logger.debug(f"Starting runner with {len(benchmarkers)} benchmarkers and a total of {njobs} jobs to submit.")

        i = j = 0
        # submit njobs to the runner
        while j < njobs and i < len(benchmarkers):
            logger.debug(f"Submitting job {j + 1}/{njobs} with benchmarker {i + 1}/{len(benchmarkers)}")
            job = benchmarkers[i].next_job()
            if job is not None:
                if not self.submit(job):
                    logger.debug(f"Job {job.solver_id} on {job.benchmark_id} was rejected by the runner.")
                else:
                    j = j + 1
            else:
                i = i + 1

        # iterate over the results
        for result in self.completions():
            logger.debug(f"Received result for job: Solver {result.get_job().solver_id} on Benchmark {result.get_job().benchmark_id}")
            if result.has_failed():
                dec_retries = 1
                if "loss of manager" in result.job.error:
                    # do not decrement retries on manager loss
                    dec_retries = 0
                else:
                    logger.error(result.job.error)
                if result.get_job().retries > 0:
                    # resubmit failed job
                    self.submit(result.get_job().clone_retry(decrement=dec_retries))
                continue
            result.get_job().job_producer.handle_result(result)
            result.get_job().job_producer.results_to_consume.put(result)
            # submit the next job
            job = None
            while job is None and i < len(benchmarkers):
                job = benchmarkers[i].next_job()
                if job is not None:
                    if not self.submit(job):
                        logger.debug(f"Job {job.solver_id} on {job.benchmark_id} was rejected by the runner.")
                        job = None  # job rejected, try next job
                else:
                    i = i + 1

        # signal the consumer thread of each benchmarker to finish and wait for it
        for benchmarker in benchmarkers:
            benchmarker.results_to_consume.put(None)
        for benchmarker in benchmarkers:
            benchmarker.result_consumer_thread.join()

    @abstractmethod
    def submit(self, job: Job) -> bool:
        """Submit a job to the external system."""
        logger.debug(f"Submitting job: Solver {job.solver_id} on Benchmark {job.benchmark_id}")
        self.jobs.append(job)
        job.mark_submitted()
        return True

    @abstractmethod
    def completed(self, job: Job) -> Result:
        """
        If the job has completed:
        - update the job's state to either FINISHED or FAILED.
        - return a Result object
        Otherwise, return None.
        """

    def completions(self, sleep_duration: float = 1):
        """
        Yield whenever the external system reports a job as done/failed.
        Stops when all jobs are either CANCELLED, FAILED or FINISHED.

        Args:
            sleep_duration (float, optional): sleep duration in s between two polls of completed jobs. Defaults to 1.
        """
        while not all(j.state in FINISHED_STATES for j in self.jobs):
            for job in self.jobs:
                if job.state == JobState.RUNNING:
                    result = self.completed(job)
                    if result is not None:
                        yield result
                    else:
                        time.sleep(sleep_duration)

    @abstractmethod
    def cancel(self, job: Job):
        """Best-effort cancellation if supported by the external system."""
        job.cancel_local()

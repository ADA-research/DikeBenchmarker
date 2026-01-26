"""
Adaptor to execution environment (cluster, SLURM, K8s, cloud API, vendor queue).
"""

from abc import ABC, abstractmethod
import time

from sustainablecompetition.benchmarkingmethods.abstract_benchmarker import AbstractBenchmarker
from sustainablecompetition.benchmarkadaptors.abstractinstance import AbstractInstanceAdaptor
from sustainablecompetition.solveradaptors.abstractexecutable import AbstractExecutable
from sustainablecompetition.benchmarkatoms import Job, JobState, Result


__all__ = ["AbstractRunner"]

FINISHED_STATES = {JobState.CANCELLED, JobState.FAILED, JobState.FINISHED}


class AbstractRunner(ABC):
    """Interface for Runners"""

    def __init__(self, solver_adaptor: AbstractExecutable = None, instance_adaptor: AbstractInstanceAdaptor = None):
        self.jobs = list[Job]()
        self.instance_adaptor = instance_adaptor
        self.solver_adaptor = solver_adaptor

    def run(self, benchmarker: AbstractBenchmarker, njobs: int = 1):
        """
        Maintains the benchmarking process and blocks until benchmarking is finished (i.e., all jobs are completed).
        Also blocks until all consumers are finished.
        """
        # submit njobs to the runner
        for _ in range(njobs):
            job = benchmarker.next_job()
            if job is not None:
                self.submit(job)

        # iterate over the results
        for result in self.completions():
            if result.has_failed():
                if result.get_job().retries > 0:
                    self.submit(result.get_job().clone_retry())  # resubmit failed job
                continue
            benchmarker.handle_result(result)
            # submit the next job
            job = benchmarker.next_job()
            if job is not None:
                self.submit(job)
            benchmarker.results_to_consume.put(result)

        # signal the consumer thread to finish
        benchmarker.results_to_consume.put(None)
        benchmarker.result_consumer_thread.join()

    @abstractmethod
    def submit(self, job: Job):
        """Submit a job to the external system."""
        self.jobs.append(job)
        job.mark_submitted()

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

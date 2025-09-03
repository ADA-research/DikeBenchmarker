"""
Adapter to execution environment (cluster, SLURM, K8s, cloud API, vendor queue).
"""

from abc import ABC, abstractmethod
from typing import Iterator
import time

from sustainablecompetition.benchmarkatoms import Job, JobState, Result


class AbstractRunner(ABC):
    """Interface for Runners"""

    def __init__(self):
        self.jobs = list[Job]()

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

    def completions(self) -> Iterator[Result]:
        """
        Must yield whenever the external system reports a job as done/failed.
        """
        while True:
            for job in [j for j in self.jobs if j.state == JobState.RUNNING]:
                result = self.completed(job)
                if result is not None:
                    yield result
                else:
                    time.sleep(1)

    @abstractmethod
    def cancel(self, job: Job):
        """Best-effort cancellation if supported by the external system."""
        job.cancel_local()

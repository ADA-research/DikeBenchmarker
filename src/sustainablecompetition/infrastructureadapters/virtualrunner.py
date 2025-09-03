"""
Virtual Runner Adapter
"""

import polars as pl

from sustainablecompetition.infrastructureadapters.abstractrunner import AbstractRunner
from sustainablecompetition.benchmarkatoms import Job, Result


class VirtualRunner(AbstractRunner):
    """
    Simulate a runner using given runtimes dataset.
    """

    def __init__(self, runtimes: pl.DataFrame):
        super().__init__()
        self.runtimes = runtimes

    def submit(self, job: Job):
        """
        Submit a function to the process pool.
        Return an id for identification of the process future.
        """
        super().submit(job)
        job.external_id = len(self.jobs) - 1

    def completed(self, job: Job) -> Result:
        """
        Return the runtime result for the solver/instance pair.
        """
        extid = job.external_id
        job = self.jobs[extid]
        instance = job.benchmark_id
        solver = job.solver_id
        runtime = self.runtimes.loc[instance, solver]
        if runtime is not None:
            return Result(job, runtime, 0)
        return None

    def cancel(self, job):
        return super().cancel(job)

"""
Virtual Runner Adapter
"""

from sustainablecompetition.infrastructureadapters.abstractrunner import AbstractRunner
from sustainablecompetition.benchmarkatoms import Job, Result
from sustainablecompetition.dataadapters.dataadapter import DataAdapter


class VirtualRunner(AbstractRunner):
    """
    Simulate a runner using given runtimes dataset.
    """

    def __init__(self, runtimes: DataAdapter):
        super().__init__()
        self.runtimes = runtimes

    def submit(self, job: Job):
        """
        Submit a function to the process pool.
        Return an id for identification of the process future.
        """
        super().submit(job)
        job.external_id = len(self.jobs) - 1
        job.mark_running()

    def completed(self, job: Job) -> Result:
        """
        Return the runtime result for the solver/instance pair.
        """
        extid = job.external_id
        job = self.jobs[extid]
        instance = job.benchmark_id
        solver = job.solver_id
        runtime = self.runtimes.get_performances(instance, solver).item()
        job.set_finished()
        return Result(job, runtime, 0)

    def cancel(self, job):
        return super().cancel(job)

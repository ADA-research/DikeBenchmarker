"""
Virtual Runner Adaptor
"""

from sustainablecompetition.infrastructureadaptors.abstractrunner import AbstractRunner
from sustainablecompetition.benchmarkatoms import Job, Result
from sustainablecompetition.dataadaptors.dataadaptor import DataAdaptor


class VirtualRunner(AbstractRunner):
    """
    Simulate a runner using given runtimes dataset.
    """

    def __init__(self, runtimes: DataAdaptor):
        super().__init__()
        self.runtimes = runtimes

    def submit(self, job: Job):
        accepted = super().submit(job)
        job.external_id = len(self.jobs) - 1
        job.mark_running()
        return accepted

    def completed(self, job: Job) -> Result:
        """
        Return the runtime result for the solver/instance pair.
        """
        extid = job.external_id
        job = self.jobs[extid]
        instance = job.benchmark_id
        solver = job.solver_id
        runtime = self.runtimes.get_performances(instance, solver)["perf"][0]
        job.set_finished()
        return Result(job, runtime, 0)

    def cancel(self, job):
        return super().cancel(job)

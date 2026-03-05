"""Virtual Runner Adaptor."""

from DIKEBenchmarker.infrastructureadaptors.abstract_runner import AbstractRunner
from DIKEBenchmarker.benchmarkatoms import Job, Result
from DIKEBenchmarker.dataadaptors.dataadaptor import DataAdaptor


class VirtualRunner(AbstractRunner):
    """Simulate a runner using given runtimes dataset."""

    def __init__(self, runtimes: DataAdaptor):
        """Initialize the virtual runner with a runtimes dataset."""
        super().__init__()
        self.runtimes = runtimes

    def submit(self, job: Job):
        """Submit a job for virtual execution."""
        self.jobs.append(job)
        job.mark_submitted()
        job.mark_running()
        return True

    def completed(self, job: Job) -> Result:
        """Return the runtime result for the solver/instance pair."""
        instance = job.benchmark_id
        solver = job.solver_id
        runtime = self.runtimes.get_performances(instance, solver)["perf"][0]
        job.set_finished()
        return Result(job, runtime, 0)

    def cancel(self, job):
        """Cancel a job."""
        return super().cancel(job)

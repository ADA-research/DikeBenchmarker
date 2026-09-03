"""Virtual Runner Adaptor."""

from DikeBenchmarker.infrastructureadaptors.abstract_runner import AbstractRunner
from DikeBenchmarker.benchmarkatoms import Job, ResourceResult, Result
from DikeBenchmarker.dataadaptors.dataadaptor import DataAdaptor


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
        result = Result(job)
        result.solver_resources = ResourceResult()
        result.solver_resources.cputime = runtime
        result.solver_resources.detail = "simulation"
        return result

    def cancel(self, job):
        """Cancel a job."""
        return super().cancel(job)

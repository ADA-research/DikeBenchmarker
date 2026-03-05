"""Benchmark Interfaces."""

from DIKEBenchmarker.benchmarkatoms import Job, Result
from DIKEBenchmarker.benchmarkingmethods.abstract_benchmarker import AbstractBenchmarker
from DIKEBenchmarker.benchmarkingmethods.instance_selectors.instance_selector import InstanceSelector
from DIKEBenchmarker.benchmarkingmethods.stopping_criterion.stopping_criteria import StoppingCriteria

__all__ = ["CombinedBenchmarker"]


class CombinedBenchmarker(AbstractBenchmarker):
    """Decides which jobs to submit next; can depend on past results/dependencies."""

    def __init__(
        self,
        selector: InstanceSelector,
        stopping_criteria: StoppingCriteria,
        benchmark_ids: list[str],
        solver_id: str,
        checker_id: str = "none",
        logroot: str = "./logs",
    ):
        """Initialize the combined benchmarker with instance selector and stopping criteria."""
        super().__init__(benchmark_ids, solver_id, checker_id, logroot)
        self.selector = selector
        self.stopping_criteria = stopping_criteria

    def next_job(self) -> Job:
        """Return the next job to submit or None if stopping."""
        if self.should_stop():
            return None
        benchmark_id = self.selector.next_benchmark_id()
        if benchmark_id is not None:
            job = Job(job_producer=self, benchmark_id=benchmark_id, solver_id=self.solver_id, checker_id=self.checker_id, logroot=self.logroot)
            self.stopping_criteria.job_submitted(job)
            return job
        return None

    def should_stop(self) -> bool:
        """Return True if the stopping criteria is met."""
        return self.stopping_criteria.should_stop()

    def handle_result(self, result: Result) -> None:
        """Handle result by passing it to the selector and stopping criteria."""
        self.selector.handle_result(result)
        self.stopping_criteria.handle_result(result)
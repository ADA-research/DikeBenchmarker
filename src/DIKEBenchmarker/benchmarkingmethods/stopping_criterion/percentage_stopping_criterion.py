"""Stopping criterion that stops after a given percentage of instances have been run."""

from DIKEBenchmarker.benchmarkingmethods.stopping_criterion.stopping_criteria import StoppingCriteria

__all__ = ["PercentageStoppingCriterion"]


class PercentageStoppingCriterion(StoppingCriteria):
    """Stopping criterion that stops after a given percentage of all benchmark instances have been run."""

    def __init__(self, benchmark_ids: list[str], percentage: float):
        """Initialize with benchmark ids and the stopping percentage threshold."""
        super().__init__()
        self.benchmark_ids = benchmark_ids
        self.percentage = percentage

    def should_stop(self) -> bool:
        """Return True when the observed instance ratio reaches the threshold."""
        if len(self.benchmark_ids) == 0:
            return True
        return len(self.selected_benchmark_ids) / len(self.benchmark_ids) >= self.percentage


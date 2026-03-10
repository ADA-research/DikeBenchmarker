"""Discrimination benchmarker implementation that submits each solver/instance pair."""

from DikeBenchmarker.benchmarkatoms import Result
from DikeBenchmarker.benchmarkingmethods.instance_selectors.instance_selector import InstanceSelector
from DikeBenchmarker.dataadaptors.dataadaptor import DataAdaptor

__all__ = ["DiscriminationInstanceSelector"]


class DiscriminationInstanceSelector(InstanceSelector):
    """Instance selector prioritizing instances by discrimination score."""

    def __init__(self, benchmark_ids: list[str], solver_id: str, data: DataAdaptor, rho: float = 1.2):
        """Initialize the selector with benchmark ids, solver id, data, and rho."""
        super().__init__(benchmark_ids, solver_id)
        self.jobs_submitted = set()
        self.data = data
        self.rho = rho

        ordered = []
        for benchmark_id in benchmark_ids:
            perf_data = data.get_performances(benchmark_id).get_column("perf")
            best_perf = perf_data.min()
            score = (perf_data >= self.rho * best_perf).sum() / perf_data.mean()
            ordered.append((score, benchmark_id))
        ordered.sort(key=lambda x: x[0])
        self.queue = [x[1] for x in ordered]

    def next_benchmark_id(self) -> str:
        """Return the next benchmark id from the ordered queue, or None."""
        if self.queue:
            benchmark_id = self.queue.pop()
            self.jobs_submitted.add(benchmark_id)
            return benchmark_id
        return None

    def handle_result(self, result: Result) -> None:
        """Handle result updates (no-op for this selector)."""
        pass

"""Variance benchmarker implementation that submits each solver/instance pair."""

from DikeBenchmarker.benchmarkatoms import Result
from DikeBenchmarker.benchmarkingmethods.instance_selectors.instance_selector import InstanceSelector
from DikeBenchmarker.dataadaptors.dataadaptor import DataAdaptor

__all__ = ["VarianceInstanceSelector"]


class VarianceInstanceSelector(InstanceSelector):
    """Instance selector that prioritizes instances based on the variance of their performance scores."""

    def __init__(self, benchmark_ids: list[str], solver_id: str, data: DataAdaptor):
        """Initialize the variance instance selector with data adaptor."""
        super().__init__(benchmark_ids, solver_id)
        self.jobs_submitted = set()
        self.data = data

        ordered = []
        for benchmark_id in benchmark_ids:
            perf_data = data.get_performances(benchmark_id).get_column("perf")
            # Perf data has columns
            # print(perf_data.columns)
            score = perf_data.var() / perf_data.mean()
            ordered.append((score, benchmark_id))
        ordered.sort(key=lambda x: x[0])
        self.queue = [x[1] for x in ordered]

    def next_benchmark_id(self) -> str:
        """Return the next benchmark id based on variance ordering or None."""
        if self.queue:
            benchmark_id = self.queue.pop()
            self.jobs_submitted.add(benchmark_id)
            return benchmark_id
        return None

    def handle_result(self, result: Result) -> None:
        """Handle result (no-op for variance selector)."""
        pass

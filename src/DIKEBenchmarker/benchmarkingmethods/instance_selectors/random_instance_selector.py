"""Random benchmarker implementation that submits each solver/instance pair."""

from typing import Optional
import random
from DIKEBenchmarker.benchmarkatoms import Result
from DIKEBenchmarker.benchmarkingmethods.instance_selectors.instance_selector import InstanceSelector

__all__ = ["RandomInstanceSelector"]


class RandomInstanceSelector(InstanceSelector):
    """Instance selector that randomly selects instances."""

    def __init__(self, benchmark_ids: list[str], solver_id: str, seed: Optional[int] = None):
        """Initialize the random instance selector with optional seed."""
        super().__init__(benchmark_ids, solver_id)
        self.jobs_submitted = set()
        self.queue = benchmark_ids[:]
        random.Random(seed).shuffle(self.queue)

    def next_benchmark_id(self) -> str:
        """Return the next randomly selected benchmark id or None."""
        if self.queue:
            benchmark_id = self.queue.pop()
            self.jobs_submitted.add(benchmark_id)
            return benchmark_id
        return None

    def handle_result(self, result: Result) -> None:
        """Handle result (no-op for random selector)."""
        pass

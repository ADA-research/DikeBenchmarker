"""
Random benchmarker implementation that submits each solver/instance pair.
"""

from typing import Optional
import random
from sustainablecompetition.benchmarkatoms import Result
from sustainablecompetition.benchmarkingmethods.instance_selectors.instance_selector import InstanceSelector

__all__ = ["RandomInstanceSelector"]


class RandomInstanceSelector(InstanceSelector):
    def __init__(self, benchmark_ids: list[str], solver_id: str, seed: Optional[int] = None):
        super().__init__(benchmark_ids, solver_id)
        self.jobs_submitted = set()
        self.queue = benchmark_ids[:]
        random.Random(seed).shuffle(self.queue)

    def next_benchmark_id(self) -> str:
        if self.queue:
            benchmark_id = self.queue.pop()
            self.jobs_submitted.add(benchmark_id)
            return benchmark_id
        return None

    def handle_result(self, result: Result) -> None:
        pass

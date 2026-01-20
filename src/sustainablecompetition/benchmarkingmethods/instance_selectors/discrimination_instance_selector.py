"""
Discrimination benchmarker implementation that submits each solver/instance pair.
"""

from typing import Optional
from sustainablecompetition.benchmarkatoms import Job, Result
from sustainablecompetition.benchmarkingmethods.instance_selectors.instance_selector import InstanceSelector
from sustainablecompetition.dataadaptors.dataadaptor import DataAdaptor

__all__ = ["DiscriminationInstanceSelector"]


class DiscriminationInstanceSelector(InstanceSelector):
    def __init__(self, benchmark_ids: list[str], solver_id: str, data: DataAdaptor, rho: float = 1.2):
        super().__init__(benchmark_ids, solver_id)
        self.jobs_submitted = set()
        self.data = data
        self.rho = rho

        ordered = []
        for benchmark_id in benchmark_ids:
            perf_data = data.get_performances(benchmark_id).get_column("perf")
            score = (perf_data >= self.rho * perf_data.median()).shape[0] / perf_data.median()
            ordered.append((score, benchmark_id))
        ordered.sort(key=lambda x: x[0])
        self.queue = [x[1] for x in ordered]

    def next_benchmark_id(self) -> str:
        if self.queue:
            benchmark_id = self.queue.pop()
            self.jobs_submitted.add(benchmark_id)
            return benchmark_id
        return None

    def handle_result(self, result: Result) -> None:
        pass

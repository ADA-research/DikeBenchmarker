"""
Variance benchmarker implementation that submits each solver/instance pair.
"""

from typing import Optional
from sustainablecompetition.benchmarkingmethods.benchmarkerinterface import Benchmarker
from sustainablecompetition.benchmarkatoms import Job, Result
from sustainablecompetition.dataadaptors.dataadaptor import DataAdaptor

__all__ = ["VarianceBenchmarker"]


class VarianceBenchmarker(Benchmarker):
    def __init__(self, benchmark_ids: list[str], solver_id: str, data: DataAdaptor):
        super().__init__(benchmark_ids, solver_id)
        self.jobs_submitted = set()
        self.data = data

        ordered = []
        for benchmark_id in benchmark_ids:
            perf_data = data.get_performances(benchmark_id).get_column("perf")
            # Perf data has columns
            # print(perf_data.columns)
            score = perf_data.var() / perf_data.median()
            ordered.append((score, benchmark_id))
        ordered.sort(key=lambda x: x[0])
        self.queue = [x[1] for x in ordered]

    def next_job(self) -> Optional[Job]:
        if self.queue:
            benchmark_id = self.queue.pop()
            self.jobs_submitted.add(benchmark_id)
            return Job(benchmark_id=benchmark_id, solver_id=self.solver_id)
        return None

    def handle_result(self, result: Result) -> None:
        pass

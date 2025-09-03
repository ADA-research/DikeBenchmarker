"""
Trivial benchmarker implementation that submits each solver/instance pair.
"""

from sustainablecompetition.benchmarkingmethods.benchmarkerinterface import Benchmarker
from sustainablecompetition.benchmarkatoms import Job, Result


class TrivialBenchmarker(Benchmarker):
    def __init__(self, benchmark_ids, solver_id):
        super().__init__(benchmark_ids, solver_id)
        self.jobs_submitted = set()

    def next_job(self) -> Job:
        # Submit each benchmark_id once, trivially
        for bid in self.benchmark_ids:
            if bid not in self.jobs_submitted:
                self.jobs_submitted.add(bid)
                return Job(benchmark_id=bid, solver_id=self.solver_id)
        return None

    def handle_result(self, result: Result) -> None:
        # Trivial implementation: do nothing
        pass

"""
Trivial benchmarker implementation that submits each solver/instance pair.
"""

from sustainablecompetition.benchmarkingmethods.benchmarkerinterface import Benchmarker
from sustainablecompetition.benchmarkatoms import Job, Result

__all__ = ["TrivialBenchmarker"]


class TrivialBenchmarker(Benchmarker):
    """
    Create jobs from a list of benchmark ids and a solver id return them one by one.
    """

    def __init__(self, benchmark_ids: list[str], solver_id: str):
        super().__init__(benchmark_ids, solver_id)
        self.jobs_submitted = set()

    def next_job(self) -> Job | None:
        """
        Return the next job to submit or None if there is nothing left to do.
        """
        for bid in self.benchmark_ids:
            if bid not in self.jobs_submitted:
                self.jobs_submitted.add(bid)
                return Job(benchmark_id=bid, solver_id=self.solver_id)
        return None

    def handle_result(self, result: Result) -> None:
        """Handle the result of a finished job (no-op for this trivial benchmarker)."""
        pass

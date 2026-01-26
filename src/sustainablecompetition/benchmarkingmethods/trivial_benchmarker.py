"""
Trivial benchmarker implementation that submits each solver/instance pair.
"""

from typing import Optional
from sustainablecompetition.benchmarkingmethods.abstract_benchmarker import AbstractBenchmarker
from sustainablecompetition.benchmarkatoms import Job, Result

__all__ = ["TrivialBenchmarker"]


class TrivialBenchmarker(AbstractBenchmarker):
    """
    Create jobs from a list of benchmark ids and a solver id return them one by one and only stops when all jobs are exhausted.
    """

    def __init__(self, benchmark_ids: list[str], solver_id: str, checker_id: str, logroot: str):
        super().__init__(benchmark_ids, solver_id, checker_id, logroot)
        self.jobs_submitted = set()

    def next_job(self) -> Optional[Job]:
        for bid in self.benchmark_ids:
            if bid not in self.jobs_submitted:
                self.jobs_submitted.add(bid)
                return Job(job_producer=self, benchmark_id=bid, solver_id=self.solver_id, checker_id=self.checker_id, logroot=self.logroot)
        return None

    def handle_result(self, result: Result) -> None:
        """Handle the result of a finished job (no-op for this trivial benchmarker)."""
        pass

    def should_stop(self):
        return len(self.jobs_submitted) >= len(self.benchmark_ids)

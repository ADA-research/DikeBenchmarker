"""Benchmark Interfaces"""

from abc import ABC, abstractmethod

from sustainablecompetition.benchmarkatoms import Job, Result

__all__ = ["Benchmarker"]


class Benchmarker(ABC):
    """
    Decides which jobs to submit next; can depend on past results/dependencies.
    """

    def __init__(self, benchmark_ids, solver_id):
        self.benchmark_ids = benchmark_ids
        self.solver_id = solver_id

    @abstractmethod
    def next_job(self) -> Job:
        """Return the next job to submit (can be None if no job is ready)."""
        raise NotImplementedError

    @abstractmethod
    def handle_result(self, result: Result) -> None:
        """Called for each finished/failed job to update planning or process results."""
        raise NotImplementedError

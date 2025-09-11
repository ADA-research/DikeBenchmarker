"""Instance Selector Interfaces"""

from abc import ABC, abstractmethod
from typing import Optional

from sustainablecompetition.benchmarkatoms import Job, Result

__all__ = ["InstanceSelector"]


class InstanceSelector(ABC):
    """
    Decides which jobs to submit next; can depend on past results/dependencies.
    """

    def __init__(self, benchmark_ids: list[str], solver_id: str):
        self.benchmark_ids = benchmark_ids
        self.solver_id = solver_id

    @abstractmethod
    def next_job(self) -> Optional[Job]:
        """Return the next job to submit (can be None if there is nothing left to do)."""
        raise NotImplementedError

    @abstractmethod
    def handle_result(self, result: Result) -> None:
        """Called for each finished/failed job to update planning or process results."""
        raise NotImplementedError

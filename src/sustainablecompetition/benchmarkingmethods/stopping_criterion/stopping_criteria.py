"""Stopping Criteria Interfaces"""

from abc import ABC, abstractmethod

from sustainablecompetition.benchmarkatoms import Result


__all__ = ["StoppingCriteria"]


class StoppingCriteria(ABC):
    """
    Decides when to stop submitting jobs.
    """

    @abstractmethod
    def should_stop(self) -> bool:
        """
        Return true if and only if the benchmarker has enough data to conclude
        """
        raise NotImplementedError

    @abstractmethod
    def handle_result(self, result: Result) -> None:
        """Called for each finished/failed job to update planning or process results."""
        raise NotImplementedError

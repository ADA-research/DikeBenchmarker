"""Stopping Criteria Interfaces"""

from abc import ABC, abstractmethod
# from typing import TYPE_CHECKING

from sustainablecompetition.benchmarkatoms import Result

# if TYPE_CHECKING:
from sustainablecompetition.benchmarkingmethods.stopping_criterion.or_stopping_criteria import OrStoppingCriteria
from sustainablecompetition.benchmarkingmethods.stopping_criterion.and_stopping_criteria import AndStoppingCriteria


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

    def __or__(self, value: "StoppingCriteria") -> "OrStoppingCriteria":
        return OrStoppingCriteria([self, value])

    def __and__(self, value: "StoppingCriteria") -> "AndStoppingCriteria":
        return AndStoppingCriteria([self, value])

"""
Abstract consumer for benchmarking results.
"""

from abc import ABC, abstractmethod

from DikeBenchmarker.benchmarkatoms import Result


__all__ = ["AbstractConsumer"]


class AbstractConsumer(ABC):
    """
    Consumes the result of the benchmarking process.
    It is guaranteed that results are processed in order.
    """

    @abstractmethod
    def consume_result(self, result: Result):
        """Process a Result.

        Args:
            result (Result): the last result obtained.
        """

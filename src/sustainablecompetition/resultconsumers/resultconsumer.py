from abc import ABC, abstractmethod

from sustainablecompetition.benchmarkatoms import Result


__all__ = ["ResultConsumer"]


class ResultConsumer(ABC):
    """Consumes the result of the benchmarking process.
    It is guaranteed that results are processed in order.
    """

    @abstractmethod
    async def consume_result(self, result: Result):
        """Process a Result.

        Args:
            result (Result): the last result obtained.
        """
        pass

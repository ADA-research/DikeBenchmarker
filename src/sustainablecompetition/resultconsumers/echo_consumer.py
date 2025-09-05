"""
Echo consumer for benchmarking results.
"""

from sustainablecompetition.benchmarkatoms import Result
from sustainablecompetition.resultconsumers.resultconsumer import ResultConsumer

__all__ = ["EchoConsumer"]


class EchoConsumer(ResultConsumer):
    """Outputs the result of the benchmarking process to the console."""

    async def consume_result(self, result: Result):
        """Output a Result.

        Args:
            result (Result): the last result obtained.
        """
        print(result)

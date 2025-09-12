"""
Lambda consumer for benchmarking results.
"""

from typing import Callable
from sustainablecompetition.benchmarkatoms import Result
from sustainablecompetition.resultconsumers.resultconsumer import ResultConsumer

__all__ = ["LambdaConsumer"]


class LambdaConsumer(ResultConsumer):
    """Applies a given function to the result."""

    def __init__(self, callback: Callable[[Result], None]):
        super().__init__()
        self.callback = callback

    def consume_result(self, result: Result):
        self.callback(result)

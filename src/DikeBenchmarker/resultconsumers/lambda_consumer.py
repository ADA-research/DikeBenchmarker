"""
Lambda consumer for benchmarking results.
"""

from typing import Callable
from DikeBenchmarker.benchmarkatoms import Result
from DikeBenchmarker.resultconsumers.abstract_consumer import AbstractConsumer

__all__ = ["LambdaConsumer"]


class LambdaConsumer(AbstractConsumer):
    """Applies a given function to the result."""

    def __init__(self, callback: Callable[[Result], None]):
        super().__init__()
        self.callback = callback

    def consume_result(self, result: Result):
        self.callback(result)

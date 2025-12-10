"""
ThenResultConsumer for benchmarking results.
"""

from sustainablecompetition.benchmarkatoms import Result
from sustainablecompetition.resultconsumers.abstract_consumer import AbstractConsumer

__all__ = ["ThenResultConsumer"]


class ThenResultConsumer(AbstractConsumer):
    """Applies a series of result consumer in order"""

    def __init__(self, consumers: list[AbstractConsumer]):
        super().__init__()
        self.consumers = consumers

    def consume_result(self, result: Result):
        for consumer in self.consumers:
            consumer.consume_result(result)

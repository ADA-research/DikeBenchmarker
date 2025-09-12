"""
Controller module for connecting benchmarking methods with infrastructure adaptors.
"""

from multiprocessing import Process, Queue
import time

from sustainablecompetition.benchmarkingmethods.benchmarkerinterface import Benchmarker
from sustainablecompetition.infrastructureadaptors.abstractrunner import AbstractRunner
from sustainablecompetition.resultconsumers.resultconsumer import ResultConsumer

__all__ = ["Controller"]


class Controller:
    """
    Connects the benchmarking method with the infrastructure adaptor.
    """

    def __init__(self, benchmarker: Benchmarker, runner: AbstractRunner, njobs: int = 1, consumers: list[ResultConsumer] = None):
        self.benchmarker = benchmarker
        self.runner = runner
        self.njobs = njobs
        self.consumers = consumers if consumers is not None else []
        # safe concurrent access to results queue to be consumed by consumers in a separate process:
        self.results_to_consume: Queue = Queue()
        self.result_consumer_process = Process(target=self._consume_results, args=(self.results_to_consume,))
        self.result_consumer_process.start()

    def _consume_results(self, results):
        while True:
            if not results.empty():
                result = results.get()
                if result is None:
                    break
                for consumer in self.consumers:
                    consumer.consume_result(result)
            else:
                time.sleep(0.1)

    def run(self):
        """
        Maintains the benchmarking process and blocks until benchmarking is finished (i.e., all jobs are completed).
        Also blocks until all consumers are finished.
        """
        # submit njobs to the runner
        for _ in range(self.njobs):
            job = self.benchmarker.next_job()
            if job is not None:
                self.runner.submit(job)
        # iterate over the results
        for result in self.runner.completions():
            self.benchmarker.handle_result(result)
            # submit the next job
            job = self.benchmarker.next_job()
            if job is not None:
                self.runner.submit(job)
            self.results_to_consume.put(result)

        # signal the consumer process to finish
        self.results_to_consume.put(None)
        self.result_consumer_process.join()

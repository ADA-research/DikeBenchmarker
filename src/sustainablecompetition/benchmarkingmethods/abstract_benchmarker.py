"""
Benchmarker Interface

Defines the interface for benchmarkers.
Implements basic functionality for registering result consumers and consuming results in a separate thread.
"""

from threading import Thread
from queue import Queue

from abc import ABC, abstractmethod
from typing import Optional

from sustainablecompetition.benchmarkatoms import Job, Result
from sustainablecompetition.infrastructureadaptors.abstractrunner import AbstractRunner

__all__ = ["AbstractBenchmarker"]


class AbstractBenchmarker(ABC):
    """
    Decides which jobs to submit next; can depend on past results/dependencies.
    """

    def __init__(self, benchmark_ids: list[str], solver_id: str):
        self.benchmark_ids = benchmark_ids
        self.solver_id = solver_id
        self.consumers = []
        # safe concurrent access to results queue to be consumed by consumers in a separate thread:
        self.results_to_consume: Queue = Queue()
        self.result_consumer_thread = Thread(target=self._consume_results, args=(self.results_to_consume,), daemon=False)
        self.result_consumer_thread.start()

    def register_consumer(self, consumer):
        """
        Register a result consumer to process results when they are available.
        """
        self.consumers.append(consumer)

    def _consume_results(self, results):
        """
        Consumes results in a separate thread.
        """
        while True:
            result = results.get()  # blocks until an item is available
            if result is None:
                break
            for consumer in self.consumers:
                consumer.consume_result(result)

    def run(self, runner: AbstractRunner, njobs: int = 1):
        """
        Maintains the benchmarking process and blocks until benchmarking is finished (i.e., all jobs are completed).
        Also blocks until all consumers are finished.
        """
        # submit njobs to the runner
        for _ in range(njobs):
            job = self.next_job()
            if job is not None:
                runner.submit(job)

        # iterate over the results
        for result in runner.completions():
            self.handle_result(result)
            # submit the next job
            job = self.next_job()
            if job is not None:
                runner.submit(job)
            self.results_to_consume.put(result)

        # signal the consumer thread to finish
        self.results_to_consume.put(None)
        self.result_consumer_thread.join()

    @abstractmethod
    def next_job(self) -> Optional[Job]:
        """Return the next job to submit (can be None if there is nothing left to do)."""
        raise NotImplementedError

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

"""Benchmarker interface.

Allows for combining different instance selectors and stopping criteria,
and for registering result consumers that process results when they are available.
"""

from threading import Thread
from queue import Queue

from abc import ABC

from DIKEBenchmarker.benchmarkatoms import Job, Result
from DIKEBenchmarker.benchmarkingmethods.instance_selectors.instance_selector import InstanceSelector
from DIKEBenchmarker.benchmarkingmethods.stopping_criterion.stopping_criteria import StoppingCriteria

__all__ = ["Benchmarker"]


class Benchmarker(ABC):
    """Decides which jobs to submit next; can depend on past results/dependencies."""

    def __init__(
        self,
        selector: InstanceSelector,
        stopping_criteria: StoppingCriteria,
        benchmark_ids: list[str],
        solver_id: str,
        checker_id: str = "none",
        logroot: str = "./logs",
    ):
        """Initialize benchmark metadata and start the result-consumer thread."""
        self.logroot = logroot
        self.benchmark_ids = benchmark_ids
        self.solver_id = solver_id
        self.checker_id = checker_id
        self.selector = selector
        self.stopping_criteria = stopping_criteria
        self.consumers = []
        # safe concurrent access to results queue to be consumed by consumers in a separate thread:
        self.results_to_consume: Queue = Queue()
        self.result_consumer_thread = Thread(target=self._consume_results, args=(self.results_to_consume,), daemon=True)
        self.result_consumer_thread.start()

    def register_consumer(self, consumer):
        """Register a result consumer to process results when they are available."""
        self.consumers.append(consumer)

    def _consume_results(self, results):
        """Consume results in a separate thread."""
        while True:
            result = results.get()  # blocks until an item is available
            if result is None:
                break
            for consumer in self.consumers:
                consumer.consume_result(result)

    def next_job(self) -> Job:
        """Return the next job to submit or None if stopping."""
        if self.should_stop():
            return None
        benchmark_id = self.selector.next_benchmark_id()
        if benchmark_id is not None:
            job = Job(job_producer=self, benchmark_id=benchmark_id, solver_id=self.solver_id, checker_id=self.checker_id, logroot=self.logroot)
            self.stopping_criteria.job_submitted(job)
            return job
        return None

    def should_stop(self) -> bool:
        """Return True if the stopping criteria is met."""
        return self.stopping_criteria.should_stop()

    def handle_result(self, result: Result) -> None:
        """Handle result by passing it to the selector and stopping criteria."""
        self.selector.handle_result(result)
        self.stopping_criteria.handle_result(result)

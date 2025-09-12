"""Benchmark Interfaces"""

from sustainablecompetition.benchmarkatoms import Job, Result
from sustainablecompetition.benchmarkingmethods.abstract_benchmarker import AbstractBenchmarker
from sustainablecompetition.benchmarkingmethods.instance_selectors.instance_selector import InstanceSelector
from sustainablecompetition.benchmarkingmethods.stopping_criterion.stopping_criteria import StoppingCriteria

__all__ = ["CombinedBenchmarker"]


class CombinedBenchmarker(AbstractBenchmarker):
    """
    Decides which jobs to submit next; can depend on past results/dependencies.
    """

    def __init__(self, selector: InstanceSelector, stopping_criteria: StoppingCriteria, benchmark_ids: list[str], solver_id: str):
        super().__init__(benchmark_ids, solver_id)
        self.selector = selector
        self.stopping_criteria = stopping_criteria

    def next_job(self) -> Job:
        return self.selector.next_job()

    def should_stop(self) -> bool:
        return self.stopping_criteria.should_stop()

    def handle_result(self, result: Result) -> None:
        self.selector.handle_result(result)
        self.stopping_criteria.handle_result(result)

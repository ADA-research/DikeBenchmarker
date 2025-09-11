"""Benchmark Interfaces"""

from sustainablecompetition.benchmarkatoms import Job, Result
from sustainablecompetition.benchmarkingmethods.benchmarkerinterface import Benchmarker
from sustainablecompetition.benchmarkingmethods.instance_selectors.instance_selector import InstanceSelector
from sustainablecompetition.benchmarkingmethods.stopping_criterion.stopping_criteria import StoppingCriteria

__all__ = ["CombinedBenchmarker"]


class CombinedBenchmarker(Benchmarker):
    """
    Decides which jobs to submit next; can depend on past results/dependencies.
    """

    def __init__(self, selector: InstanceSelector, stopping_criteria: StoppingCriteria, benchmark_ids: list[str], solver_id: str):
        self.benchmark_ids = benchmark_ids
        self.solver_id = solver_id
        self.selector = selector
        self.stopping_criteria = stopping_criteria

    def next_job(self) -> Job:
        return self.selector.next_job()

    def should_stop(self) -> bool:
        return self.stopping_criteria.should_stop()

    def handle_result(self, result: Result) -> None:
        self.selector.handle_result(result)
        self.stopping_criteria.handle_result(result)

"""Stopping criterion that stops when a minimum ranking accuracy is reached."""

import importlib

from sustainablecompetition.benchmarkatoms import Result
from sustainablecompetition.benchmarkingmethods.stopping_criterion.stopping_criteria import StoppingCriteria
from sustainablecompetition.dataadaptors.sqlite_dataadaptor import SqlDataAdaptor

__all__ = ["MinimumAccuracyStoppingCriterion"]


class MinimumAccuracyStoppingCriterion(StoppingCriteria):
    """Stopping criterion that stops when a minimum ranking accuracy is reached."""

    def __init__(self, benchmark_ids: list[str], min_accuracy: float):
        super().__init__()
        self.benchmark_ids = benchmark_ids
        self.min_accuracy = min_accuracy
        self.selected_benchmark_ids = []
        db_path = importlib.resources.files("sustainablecompetition.data").joinpath("sustainablecompetition.db")
        self.db_adaptor = SqlDataAdaptor(db_path)
        self.solvers = self.db_adaptor.get_all_solver_ids()
        self.instance_performances = {}
        performances = [
            (solver_id, sum([self.db_adaptor.get_performances(solver_id=solver_id, benchmark_id=benchmark_id) for benchmark_id in self.benchmark_ids]))
            for solver_id in self.solvers
        ]
        sorted_solvers = sorted(performances, key=lambda x: x[1])
        self.sorted_solver_ids = [solver_id for solver_id, _ in sorted_solvers]

    def should_stop(self) -> bool:
        if len(self.selected_benchmark_ids) == 0:
            return False
        total_pairs = len(self.solvers) * (len(self.solvers) - 1) // 2

        performances = [
            (solver_id, sum([self.db_adaptor.get_performances(solver_id=solver_id, benchmark_id=benchmark_id) for benchmark_id in self.selected_benchmark_ids]))
            for solver_id in self.solvers
        ]
        sorted_solvers = sorted(performances, key=lambda x: x[1])
        sorted_solver_ids = [solver_id for solver_id, _ in sorted_solvers]

        correct_pairs = 0
        for i in range(len(self.solvers)):
            for j in range(i + 1, len(self.solvers)):
                solver_i = self.sorted_solver_ids[i]
                solver_j = self.sorted_solver_ids[j]
                idx_i = sorted_solver_ids.index(solver_i)
                idx_j = sorted_solver_ids.index(solver_j)
                if idx_i < idx_j:
                    correct_pairs += 1

        accuracy = correct_pairs / total_pairs
        return accuracy >= self.min_accuracy

    def handle_result(self, result: Result) -> None:
        self.selected_benchmark_ids.append(result.job.benchmark_id)

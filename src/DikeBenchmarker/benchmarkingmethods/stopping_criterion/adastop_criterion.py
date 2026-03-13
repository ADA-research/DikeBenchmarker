"""Stopping criterion based on the AdaStop sequential permutation testing framework."""

from DikeBenchmarker.benchmarkatoms import Result
import numpy as np
from adastop import MultipleAgentsComparator

from DikeBenchmarker.benchmarkingmethods.stopping_criterion.stopping_criteria import StoppingCriteria
from DikeBenchmarker.dataadaptors.dataadaptor import DataAdaptor

__all__ = ["AdaStopCriterion"]


class AdaStopCriterion(StoppingCriteria):
    """Stopping criterion using AdaStop's sequential permutation test.

    Compares a challenger solver against a set of reference solvers using
    MultipleAgentsComparator. Stops when all pairwise comparisons are decided.
    """

    def __init__(
        self,
        benchmark_ids: list[str],
        challenger_id: str,
        solvers_challenged: list[str],
        alpha: float,
        db_adaptor: DataAdaptor,
        B: int = 10000,
    ):
        """Initialize with benchmark ids, challenger, compared solvers, and AdaStop settings.

        Parameters
        ----------
        benchmark_ids : list[str]
            All available benchmark instance IDs.
        challenger_id : str
            ID of the solver being evaluated (agent 0 in AdaStop).
        solvers_challenged : list[str]
            IDs of solvers to compare the challenger against.
        alpha : float
            Significance level for the permutation tests.
        db_adaptor : DataAdaptor
            Adaptor for fetching performance data.
        B : int
            Number of random permutations used to approximate the test distribution.
        """
        super().__init__()
        self.benchmark_ids = benchmark_ids
        self.db_adaptor = db_adaptor
        self.challenger = challenger_id
        self.solvers_challenged = list(solvers_challenged)
        all_agents = [challenger_id] + self.solvers_challenged

        comparisons = np.array([(0, i + 1) for i in range(len(self.solvers_challenged))])
        self.comparator = MultipleAgentsComparator(n=1, K=len(benchmark_ids), B=B, comparisons=comparisons, alpha=alpha)
        self.eval_values = {agent: [] for agent in all_agents}

    def should_stop(self) -> bool:
        """Return True when AdaStop has reached a decision on all pairwise comparisons."""
        return self.comparator.is_finished

    def handle_result(self, result: Result) -> None:
        """Called for each finished/failed job to update planning or process results."""
        if self.comparator.is_finished:
            return
        job = result.get_job()
        bench_id = job.benchmark_id

        for solver_id in self.eval_values:
            perf = self.db_adaptor.get_performances(inst_hash=bench_id, solver_id=solver_id).get_column("perf")[0]
            self.eval_values[solver_id].append(perf)

        self.comparator.partial_compare(self.eval_values, verbose=False)
        return self.comparator.is_finished

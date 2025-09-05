"""
SAT Solver Adaptor
"""

from sustainablecompetition.solveradaptors.abstractsolver import AbstractSolverAdaptor


class SATSolverAdaptor(AbstractSolverAdaptor):
    """Maintain paths to solvers and make them accessible by their IDs"""

    # Maps solver ids to solver paths
    registry = {}

    def get_path(self, solver_id: str) -> str:
        """
        Get the file path for a given solver ID.
        """
        return self.registry[solver_id]

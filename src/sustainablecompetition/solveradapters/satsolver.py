"""
SAT Solver Adapter
"""

from sustainablecompetition.solveradapters.abstractsolver import AbstractSolverAdapter

class SATSolverAdapter(AbstractSolverAdapter):
    """ Maintain paths to solvers and make them accessible by their IDs """

    # Maps solver ids to solver paths
    registry = {}
    
    def get_path(self, solver_id: str) -> str:
        """
        Get the file path for a given solver ID.
        """
        return self.registry[solver_id]

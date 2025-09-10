"""
SAT Solver Adaptor
"""

from sustainablecompetition.solveradaptors.abstractsolver import AbstractSolverAdaptor


class SATSolverAdaptor(AbstractSolverAdaptor):
    """Maintain paths to solvers and make them accessible by their IDs"""

    # Maps solver ids to solver paths
    registry = {}

    def register_solver(self, solver_id: str, solver_path: str):
        """
        Register a solver with its ID and path.
        """
        self.registry[solver_id] = solver_path

    def get_path(self, solver_id: str) -> str:
        """
        Get the file path for a given solver ID.
        """
        return self.registry[solver_id]

    def parse_result(self, solver_output_path: str):
        """
        Extract the result from the solver file
        """
        with open(solver_output_path, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("s "):
                    result = line.strip().split(maxsplit=1)[1]
                    return result
        return None

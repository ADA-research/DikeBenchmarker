"""
SAT Solver Adaptor
"""

from sustainablecompetition.solveradaptors.abstractexecutable import AbstractExecutable


class SolverAdaptor(AbstractExecutable):
    """Maintain paths to solvers and make them accessible by their IDs"""

    def __init__(self, serialized: dict = None):
        super().__init__(serialized)

    def format_command(self, xid: str, xbin: str, inst: str, cert: str) -> str:
        """Get the command line for a given solver ID, replacing placeholders."""
        return self.registry[xid][1].replace("$BIN", xbin).replace("$INST", inst).replace("$CERT", cert)

    def parse_result(self, outfile: str):
        """Extract the result from the solver file."""
        with open(outfile, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("s "):
                    result = line.strip().split(maxsplit=1)[1]
                    return result
        return None

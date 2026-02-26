"""SAT Solver Adaptor."""

from sustainablecompetition.solveradaptors.abstractexecutable import AbstractExecutable


class SolverAdaptor(AbstractExecutable):
    """Maintain paths to solvers and make them accessible by their IDs."""

    def __init__(self, serialized: dict = None):
        """Initialize the SolverAdaptor with a registry, or from a serialized dictionary if provided."""
        super().__init__(serialized)

    def format_command(self, xid: str, binaries: list[str], instance: str, certificate: str) -> str:
        """Get the command line for a given solver ID, replacing placeholders."""
        result = self._format_base(xid, binaries)
        result = self._format_extra(result, instance, certificate)
        return result

    def _format_extra(self, base: str, instance: str, certificate: str) -> str:
        """Get the command line for a given solver ID, replacing placeholders."""
        return base.replace("$INST", instance).replace("$CERT", certificate)

    def parse_result(self, outfile: str):
        """Extract the result from the solver file."""
        with open(outfile, "r", encoding="utf-8") as f:
            for line in f:
                if line.startswith("s "):
                    result = line.strip().split(maxsplit=1)[1]
                    return result
        return None

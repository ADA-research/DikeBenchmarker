"""SAT Solver Adaptor."""

import os

from DikeBenchmarker.benchmarkatoms import SolverResult

from DikeBenchmarker.solveradaptors.abstractexecutable import AbstractExecutable


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

    def parse_result(self, outfile: str) -> SolverResult:
        """Classify the solver verdict."""
        if not os.path.exists(outfile):
            return SolverResult(SolverResult.State.ERROR, detail="no solver output")

        with open(outfile, "r", encoding="utf-8") as f:
            for line in f:
                stripped = line.strip()
                if stripped.startswith("s "):
                    verdict = stripped[2:].strip()
                    if verdict.startswith("SAT"):
                        return SolverResult(SolverResult.State.SAT)
                    if verdict.startswith("UNSAT"):
                        return SolverResult(SolverResult.State.UNSAT)
                    if verdict == "UNKNOWN":
                        return SolverResult(SolverResult.State.UNKNOWN)
                    return SolverResult(SolverResult.State.ERROR, detail=verdict)

        return SolverResult(SolverResult.State.ERROR, detail="no solver verdict")

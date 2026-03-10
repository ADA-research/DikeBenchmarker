"""Provides access to execution wrappers like runexec, runlim, or benchexec.

Resolves the paths to the wrapper binaries and constructs command-line arguments using the specified resource limits.
"""

from DikeBenchmarker.solveradaptors.abstractexecutable import AbstractExecutable


__all__ = ["ExecutionWrapper"]


class ExecutionWrapper(AbstractExecutable):
    """A class to manage execution wrappers."""

    def __init__(self, mem=64 * 1024, cputime=3600, walltime=7200, serialized: dict = None):
        """Initialize the ExecutionWrapper with resource limits and registry, or from a serialized dictionary if provided."""
        super().__init__(serialized)
        if "runsolver" not in self.registry:
            self.register(
                "runsolver",
                ["./external/runsolver"],
                "$BIN0 --wall-clock-limit $WALLTIME --cpu-limit $CPUTIME --vsize-limit $MEMORY --var $WRAPPER_OUTPUT --solver-data $WRAPPED_OUTPUT sh -c '$WRAPPED_COMMAND'",
                None,
            )
        self.memorylimit = serialized.get("memorylimit", 64 * 1024) if serialized else mem
        self.cputimelimit = serialized.get("cputimelimit", 3600) if serialized else cputime
        self.walltimelimit = serialized.get("walltimelimit", 7200) if serialized else walltime
        if self.walltimelimit < self.cputimelimit:
            self.walltimelimit = self.cputimelimit * 2  # ensure walltime is always larger than cputime

    def to_dict(self) -> dict:
        """Convert the execution wrapper to a dictionary representation."""
        return {
            "registry": self.registry,
            "memorylimit": self.memorylimit,
            "cputimelimit": self.cputimelimit,
            "walltimelimit": self.walltimelimit,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "ExecutionWrapper":
        """Create an execution wrapper from a dictionary representation."""
        return cls(serialized=data)

    def set_resource_limits(self, cputimelimit: int = None, walltimelimit: int = None, memorylimit: int = None):
        """Set resource limits if specified."""
        self.memorylimit = memorylimit or self.memorylimit
        self.cputimelimit = cputimelimit or self.cputimelimit
        self.walltimelimit = walltimelimit or self.walltimelimit

    def format_command(self, xid: str, binaries: list[str], wrapped_cmd: str, wrapper_output: str, wrapped_output: str) -> str:
        """Return the command line to run the execution wrapper with parameters."""
        result = self._format_base(xid, binaries)
        result = self._format_extra(result, wrapped_cmd, wrapper_output, wrapped_output)
        return result

    def _format_extra(self, base: str, wrapped_cmd: str, wrapper_output: str, wrapped_output: str) -> str:
        """Construct the commandline specific to runsolver with the specified resource limits."""
        return (
            base.replace("$WRAPPED_COMMAND", wrapped_cmd)
            .replace("$WRAPPER_OUTPUT", wrapper_output)
            .replace("$WRAPPED_OUTPUT", wrapped_output)
            .replace("$WALLTIME", str(self.walltimelimit))
            .replace("$CPUTIME", str(self.cputimelimit))
            .replace("$MEMORY", str(self.memorylimit))
        )

    def parse_result(self, outfile: str):
        """Parse the runsolver log output to extract runtime statistics.

        Parameters:
        - tool_output: Path to the runsolver log output file.

        Returns:
        - dictionary with keys 'walltime', 'cputime', 'memory', 'timeout', 'memout', and 'exitstatus'.
        """
        result = {
            "walltime": None,
            "cputime": None,
            "memory": None,
            "timeout": False,
            "memout": False,
            "exitstatus": None,
        }

        with open(outfile, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("WCTIME="):
                    result["walltime"] = float(line.split("=", 1)[1].strip())
                elif line.startswith("CPUTIME="):
                    result["cputime"] = float(line.split("=", 1)[1].strip())
                elif line.startswith("MAXRSS="):
                    result["memory"] = int(line.split("=", 1)[1].strip())
                elif line.startswith("TIMEOUT="):
                    result["timeout"] = line.split("=", 1)[1].strip().lower() == "true"
                elif line.startswith("MEMOUT="):
                    result["memout"] = line.split("=", 1)[1].strip().lower() == "true"
                elif line.startswith("EXITSTATUS="):
                    result["exitstatus"] = int(line.split("=", 1)[1].strip())

        return result

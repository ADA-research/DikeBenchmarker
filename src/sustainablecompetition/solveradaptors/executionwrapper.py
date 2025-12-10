"""
This module provides Wrapper classes to manage execution wrappers like runexec, runlim, and benchexec.
It resolves the paths to these binaries and constructs command-line arguments based on specified resource limits.
"""

from sustainablecompetition.solveradaptors.abstractexecutable import AbstractExecutable


__all__ = ["ExecutionWrapper"]


class ExecutionWrapper(AbstractExecutable):
    """
    A class to manage execution wrappers.
    """

    def __init__(self, mem=64 * 1024, cputime=3600, walltime=3700, serialized: dict = None):
        """Initialize the ExecutionWrapper with resource limits and registry, or from a serialized dictionary if provided."""
        super().__init__(serialized)
        if "runsolver" not in self.registry:
            self.register(
                "runsolver",
                "./external/runsolver",
                "$BIN --wall-clock-limit $WALLTIME --cpu-limit $CPUTIME --vsize-limit $MEMORY --var $TOOLOUT --solver-data $SOLVEROUT --output-limit 10,110 $SOLVECMD",
            )
        self.memorylimit = serialized.get("memorylimit", 64 * 1024) if serialized else mem
        self.cputimelimit = serialized.get("cputimelimit", 3600) if serialized else cputime
        self.walltimelimit = serialized.get("walltimelimit", 3700) if serialized else walltime

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

    def format_command(self, xid: str, xbin: str, scmd: str, tooloutput: str, solveroutput: str) -> str:
        """Construct the commandline specific to runsolver with the specified resource limits."""
        return (
            self.registry[xid][1]
            .replace("$BIN", xbin)
            .replace("$SOLVECMD", scmd)
            .replace("$WALLTIME", str(self.walltimelimit))
            .replace("$CPUTIME", str(self.cputimelimit))
            .replace("$MEMORY", str(self.memorylimit))
            .replace("$TOOLOUT", tooloutput)
            .replace("$SOLVEROUT", solveroutput)
        )

    def parse_result(self, outfile: str):
        """
        Parse the runsolver log output to extract runtime statistics.
        Parameters:
        - tool_output: Path to the runsolver log output file.
        Returns:
        A dictionary with keys 'walltime', 'cputime', 'memory', 'timeout', 'memout', and 'exitstatus'.
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

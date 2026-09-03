"""Provides access to execution wrappers like runexec, runlim, or benchexec.

Resolves the paths to the wrapper binaries and constructs command-line arguments using the specified resource limits.
"""

import importlib.resources
import os

from DikeBenchmarker.benchmarkatoms import ResourceResult
from DikeBenchmarker.solveradaptors.abstractexecutable import AbstractExecutable


__all__ = ["ExecutionWrapper"]

_RUNSOLVER_BIN = str(importlib.resources.files("DikeBenchmarker.external").joinpath("runsolver"))


class ExecutionWrapper(AbstractExecutable):
    """A class to manage execution wrappers."""

    def __init__(self, mem=64 * 1024, cputime=3600, walltime=7200, serialized: dict = None):
        """Initialize the ExecutionWrapper with resource limits and registry, or from a serialized dictionary if provided."""
        super().__init__(serialized)
        if "runsolver" not in self.registry:
            self.register(
                "runsolver",
                [_RUNSOLVER_BIN],
                "$BIN0 --wall-clock-limit $WALLTIME --cpu-limit $CPUTIME --rss-swap-limit $MEMORY"
                " --watcher-data $WATCHER_OUTPUT --var $WRAPPER_OUTPUT"
                " --solver-data $WRAPPED_OUTPUT sh -c '$WRAPPED_COMMAND'",
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

    def format_command(self, xid: str, binaries: list[str], wrapped_cmd: str, wrapper_output: str, wrapped_output: str, watcher_output: str) -> str:
        """Return the command line to run the execution wrapper with parameters."""
        if not wrapped_cmd:
            return ""
        result = self._format_base(xid, binaries)
        result = self._format_extra(result, wrapped_cmd, wrapper_output, wrapped_output, watcher_output)
        return result

    def _format_extra(self, base: str, wrapped_cmd: str, wrapper_output: str, wrapped_output: str, watcher_output: str) -> str:
        """Construct the commandline specific to runsolver with the specified resource limits."""
        return (
            base.replace("$WRAPPED_COMMAND", wrapped_cmd)
            .replace("$WATCHER_OUTPUT", watcher_output)
            .replace("$WRAPPER_OUTPUT", wrapper_output)
            .replace("$WRAPPED_OUTPUT", wrapped_output)
            .replace("$WALLTIME", str(self.walltimelimit))
            .replace("$CPUTIME", str(self.cputimelimit))
            .replace("$MEMORY", str(self.memorylimit))
        )

    def parse_result(self, wrapper_file: str, watcher_file: str) -> ResourceResult:
        """Parse wrapper record + watcher log into resource-based metrics."""
        if not os.path.exists(wrapper_file):
            return ResourceResult(ResourceResult.State.NONE, detail="no wrapper output")

        cputime = walltime = memory = None
        state = ResourceResult.State.SUCCESS
        with open(wrapper_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("WCTIME="):
                    walltime = float(line.split("=", 1)[1])
                elif line.startswith("CPUTIME="):
                    cputime = float(line.split("=", 1)[1])
                elif line.startswith("MAXVM="):
                    memory = int(line.split("=", 1)[1]) / 1024
                elif line.startswith("TIMEOUT=") and line.split("=", 1)[1].lower() == "true":
                    state = ResourceResult.State.TIMEOUT
                elif line.startswith("MEMOUT=") and line.split("=", 1)[1].lower() == "true":
                    state = ResourceResult.State.MEMOUT

        if not os.path.exists(watcher_file):
            return ResourceResult(state, cputime=cputime, walltime=walltime, memory=memory, detail="no watcher output")

        detail = None
        with open(watcher_file, "r", encoding="utf-8") as f:
            for line in f:
                # trust the watcher over the TIMEOUT/MEMOUT flags above (runsolver quirks)
                if "Maximum memory exceeded" in line:
                    state = ResourceResult.State.MEMOUT
                    detail = "runsolver memory limit exceeded"
                    break
                if "Child ended because it received signal 24 (SIGXCPU)" in line:
                    state = ResourceResult.State.TIMEOUT
                    detail = "cpu time limit exceeded (SIGXCPU)"
                    break
                if "Child ended because it received signal 9 (SIGKILL)" in line:
                    state = ResourceResult.State.ERROR
                    detail = "killed (SIGKILL via exit 9)"
                    break
                if line.startswith("Child status: "):
                    code = line.split(":", 1)[1].strip()
                    if code == "137":
                        # external kill (SLURM OOM-killer)
                        state = ResourceResult.State.ERROR
                        detail = "killed (SIGKILL via exit 137)"
                    elif code != "0":
                        detail = f"nonzero exit (code {code})"
                    break

        return ResourceResult(state, cputime=cputime, walltime=walltime, memory=memory, detail=detail)

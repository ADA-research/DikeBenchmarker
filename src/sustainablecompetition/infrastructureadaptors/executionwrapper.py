"""
This module provides Wrapper classes to manage execution wrappers like runexec, runlim, and benchexec.
It resolves the paths to these binaries and constructs command-line arguments based on specified resource limits.
"""

import os
from typing import List
from abc import ABC, abstractmethod


__all__ = ["AbstractExecutionWrapper", "RunSolverWrapper"]


class AbstractExecutionWrapper(ABC):
    """
    Abstract base class for execution wrappers.
    """

    @abstractmethod
    def set_resource_limits(self, cputimelimit: int = None, walltimelimit: int = None, memorylimit: int = None):
        """
        Set resource limits for the execution wrapper.
        """
        pass

    @abstractmethod
    def set_outputs(self, tooloutput: str, solveroutput: str, headlimit: int = 10, taillimit: int = 10):
        """
        Set the output file for the solver's output.
        """
        pass

    @abstractmethod
    def get_command(self) -> List[str]:
        """
        Construct the commandline with the specified resource limits.
        """
        pass

    @abstractmethod
    def get_binary_path(self) -> str:
        """
        Return the path to the execution wrapper binary.
        """
        pass

    @abstractmethod
    def get_command_args(self) -> List[str]:
        """
        Return the command line arguments for the execution wrapper, excluding the binary path.
        """
        pass

    @abstractmethod
    def parse_result(self, tool_output_path: str):
        """
        Parse the tool output and extract relevant information.
        """
        pass


class RunSolverWrapper(AbstractExecutionWrapper):
    """
    A class to manage the "runsolver" execution wrapper.
    """

    def __init__(self, binpath: str = "./external/runsolver"):
        if not os.path.isfile(binpath) and not os.access(binpath, os.X_OK):
            raise FileNotFoundError(f"runsolver binary not found or not executable at {binpath}")
        self.cmd = [binpath]

    def set_resource_limits(self, cputimelimit: int = None, walltimelimit: int = None, memorylimit: int = None):
        """
        Set resource limits for the runsolver command.
        """
        if memorylimit is not None:
            self.cmd += ["--vsize-limit", str(memorylimit)]
        if walltimelimit is not None:
            self.cmd += ["--time-limit", str(walltimelimit)]
        if cputimelimit is not None:
            self.cmd += ["--cpu-limit", str(cputimelimit)]

    def set_outputs(self, tooloutput: str, solveroutput: str, headlimit: int = 10, taillimit: int = 20):
        """
        Set the output file for the solver's output.
        Parameters:
        - tooloutput: Path to the file where runsolver will write its log output.
        - solveroutput: Path to the file where the solver's output will be written.
        - headlimit: Number of megabytes from the start of the solver output to include in the solver output file.
        - taillimit: Number of megabytes from the end of the solver output to include in the solver output file.
        """
        self.cmd += ["--var", tooloutput]
        self.cmd += ["--solver-data", solveroutput]
        self.cmd += ["--output-limit", ",".join([str(headlimit), str(taillimit)])]

    def get_command(self) -> List[str]:
        """
        Construct the commandline specific to runsolver with the specified resource limits.
        """
        return self.cmd

    def get_binary_path(self) -> str:
        """
        Return the path to the runsolver binary.
        """
        return self.cmd[0]

    def get_command_args(self) -> List[str]:
        """
        Return the command line arguments for runsolver, excluding the binary path.
        """
        return self.cmd[1:]

    def parse_result(self, tool_output_path: str):
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

        with open(tool_output_path, "r", encoding="utf-8") as f:
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

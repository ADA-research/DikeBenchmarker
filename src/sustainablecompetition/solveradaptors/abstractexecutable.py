"""Abstract Executable"""

import csv

from abc import ABC, abstractmethod


class AbstractExecutable(ABC):
    """Interface for Executables such as Solvers or Execution Wrappers."""

    registry = {}

    def __init__(self, serialized: dict = None):
        self.registry = serialized.get("registry", {}) if serialized else {}

    def register(self, xid: str, sbin: list[str], sfmt: str, checker: str = None):
        """Register an executable with its path and command format."""
        self.registry[xid] = (sbin, sfmt, checker)

    def read_registry(self, registry_path: str):
        """Read a CSV file containing id, command, and format to populate the registry."""
        with open(registry_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, fieldnames=["id", "bin", "fmt", "checker"], delimiter=";")
            for row in reader:
                self.register(row["id"], row["bin"].split(","), row["fmt"], row["checker"] if "checker" in row else None)

    def get_ids(self) -> list[str]:
        """Return a list of available solver IDs."""
        return list(self.registry.keys())

    def get_binaries(self, xid: str) -> list[str]:
        """Return the binary paths for a given executables ID."""
        return self.registry[xid][0]

    def get_checker(self, xid: str) -> str:
        """Return the checker command for a given executable ID."""
        return self.registry[xid][2]

    @abstractmethod
    def format_command(self, *args, **kwargs) -> str:
        """Return the command line to run the executable with parameters."""

    @abstractmethod
    def parse_result(self, outfile: str):
        """Extract the result from the solver file."""

    def to_dict(self) -> dict:
        """Convert the executable to a dictionary representation."""
        return {"registry": self.registry}

    @classmethod
    def from_dict(cls, data: dict) -> "AbstractExecutable":
        """Create an executable from a dictionary representation."""
        return cls(data)

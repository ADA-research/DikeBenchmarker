"""Abstract Executable"""

import csv

from abc import ABC, abstractmethod


class AbstractExecutable(ABC):
    """Interface for Executables such as Solvers or Execution Wrappers."""

    registry = {}

    def __init__(self, serialized: dict = None):
        self.registry = serialized.get("registry", {}) if serialized else {}

    def register(self, xid: str, sbin: str, sfmt: str):
        """Register an executable with its path and command format."""
        self.registry[xid] = (sbin, sfmt)

    def read_registry(self, registry_path: str):
        """Read a CSV file containing id, command, and format to populate the registry."""
        with open(registry_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f, fieldnames=["id", "bin", "fmt"], delimiter=";")
            for row in reader:
                self.register(row["id"], row["bin"], row["fmt"])

    def get_ids(self) -> list[str]:
        """Return a list of available solver IDs."""
        return list(self.registry.keys())

    def get_binary(self, xid: str) -> str:
        """Return the binary path for a given executable ID."""
        return self.registry[xid][0]

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

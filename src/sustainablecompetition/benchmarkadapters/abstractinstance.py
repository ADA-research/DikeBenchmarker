"""Abstract Instance Adapter"""

from abc import ABC, abstractmethod


class AbstractInstanceAdapter(ABC):
    """Interface for Instance Adapters"""

    @abstractmethod
    def get_path(self, instance_id: str) -> str:
        """Return the path to the instance file."""
        raise NotImplementedError("Subclasses must implement get_instance_path()")

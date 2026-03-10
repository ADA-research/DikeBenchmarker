"""Abstract Instance Adaptor"""

from abc import ABC, abstractmethod


class AbstractInstanceAdaptor(ABC):
    """Interface for Instance Adaptors"""

    @abstractmethod
    def get_path(self, instance_id: str) -> str:
        """Return the path to the instance file."""
        raise NotImplementedError("Subclasses must implement get_instance_path()")

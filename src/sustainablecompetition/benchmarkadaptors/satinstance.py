"""
SAT Instance Adaptor
"""

import os
import re
from typing import Optional
import requests

from sustainablecompetition.benchmarkadaptors.abstractinstance import AbstractInstanceAdaptor


__all__ = ["SATInstanceAdaptor"]


class SATInstanceAdaptor(AbstractInstanceAdaptor):
    """Maintain paths to sat instances and make them accessible by their IDs"""

    # Maps instance ids to instance paths
    registry = {}

    def __init__(self, local_folder: Optional[str] = None, timeout: tuple[float, float] = (5, 300)):
        """
        Args:
            local_folder (str, optional): Folder in which to save downloaded instances. Defaults to None.
            timeout (tuple[float, float], optional): (connection_timeout, read_timeout) in seconds. Defaults to (5, 300).
        """
        self.local_folder = local_folder or os.path.dirname(__file__)
        self.timeout = timeout

    def get_path(self, instance_id: str) -> str:
        """
        Get the file path for a given instance ID, downloading it if necessary.
        """
        if instance_id not in self.registry:
            instance_path = self.download_instance(instance_id)
            self.registry[instance_id] = instance_path
        return self.registry[instance_id]

    def download_instance(self, instance_id: str) -> str:
        """
        Download a SAT instance file from the benchmark database.
        Returns the local file path.
        """
        url = f"https://benchmark-database.de/file/{instance_id}"
        response = requests.get(url, timeout=self.timeout)
        response.raise_for_status()
        content_disposition = response.headers.get("Content-Disposition")
        if content_disposition and "filename=" in content_disposition:
            filename_match = re.search(r'filename="?([^"]+)"?', content_disposition)
            filename = filename_match.group(1) if filename_match else instance_id
        else:
            filename = instance_id
        instance_path = os.path.join(self.local_folder, filename)
        with open(instance_path, "wb") as f:
            f.write(response.content)
        return instance_path

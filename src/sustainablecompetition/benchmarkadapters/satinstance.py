"""
SAT Instance Adapter
"""

import os
import re
import requests

from sustainablecompetition.benchmarkadapters.abstractinstance import AbstractInstanceAdapter


class SATInstanceAdapter(AbstractInstanceAdapter):
    """Maintain paths to sat instances and make them accessible by their IDs"""

    # Maps instance ids to instance paths
    registry = {}

    def get_path(self, instance_id: str) -> str:
        """
        Get the file path for a given instance ID, downloading it if necessary.
        """
        if not instance_id in self.registry:
            instance_root = os.path.dirname(__file__)
            instance_path = self.download_instance(instance_id, instance_root)
            self.registry[instance_id] = instance_path
        return self.registry[instance_id]

    def download_instance(self, instance_id: str, instance_root: str) -> str:
        """
        Download a SAT instance file from the benchmark database.
        Returns the local file path.
        """
        url = f"https://benchmark-database.de/file/{instance_id}"
        response = requests.get(url, timeout=(5, 300))
        response.raise_for_status()
        content_disposition = response.headers.get("Content-Disposition")
        if content_disposition and "filename=" in content_disposition:
            filename_match = re.search(r'filename="?([^"]+)"?', content_disposition)
            filename = filename_match.group(1) if filename_match else instance_id
        else:
            filename = instance_id
        instance_path = os.path.join(instance_root, filename)
        with open(instance_path, "wb") as f:
            f.write(response.content)
        return instance_path

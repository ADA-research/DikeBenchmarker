"""
SAT Instance Adaptor
"""

import os
import re
import sqlite3
import requests
from gbd_core.api import GBD

from DikeBenchmarker.benchmarkadaptors.abstractinstance import AbstractInstanceAdaptor


__all__ = ["SATInstanceAdaptor"]


class SATInstanceAdaptor(AbstractInstanceAdaptor):
    """Maintain paths to sat instances and make them accessible by their IDs"""

    def __init__(self, local_folder: str = "instances/sat/", gbd: str = "instances/cnf_data.db", timeout: tuple[float, float] = (5, 300)):
        """
        Args:
            local_folder (str): Folder in which to save downloaded instances. Defaults to 'instances/sat'.
            gbd (str): Path to the local copy of the gbd database. Defaults to 'instances/cnf_data.db'.
            timeout (tuple[float, float]): (connection_timeout, read_timeout) in seconds. Defaults to (5, 300).
        """
        self.local_folder = local_folder or os.path.dirname(__file__)
        self.gbd = gbd or os.path.join(os.path.dirname(__file__), "cnf_data.db")
        self.timeout = timeout
        # initialize cnf_data.db if empty
        if not os.path.isfile(self.gbd):
            sqlite3.connect(self.gbd).close()
        with GBD([self.gbd]) as db:
            if "local" not in db.get_features():
                db.create_feature("local")

    def get_local_path(self, instance_id: str) -> bool:
        """
        Check whether an instance with instance_id is available locally.
        Query the GBD database for local path information.
        If a path is found and the file exists, return the path.
        Otherwise, clear any stale entries in the database and return None.
        """
        with GBD([self.gbd]) as db:
            result = db.query(hashes=[instance_id], resolve=["local"], collapse="min")
            if len(result) == 0:
                return None
            path = result["local"][0]
            if not os.path.isfile(path):
                db.reset_values("local", values=[path], hashes=[instance_id])
                return None
            return path

    def get_path(self, instance_id: str) -> str:
        """
        Get the file path for a given instance ID, downloading it if necessary.
        """
        instance_path = self.get_local_path(instance_id)
        if instance_path is not None:
            return instance_path
        instance_path = self.download_instance(instance_id)
        return instance_path

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
        with GBD([self.gbd]) as db:
            db.set_values("local", instance_path, hashes=[instance_id])
        return instance_path

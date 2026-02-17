import polars as pl
from typing import Optional

from sustainablecompetition.dataadaptors.dataadaptor import DataAdaptor


__all__ = ["CsvDataAdaptor"]


class CsvDataAdaptor(DataAdaptor):
    """
    Implement the data adaptor for csv data.
    """

    def __init__(self, environments_path: str, instances_path: str, solvers_path: str, performances_path: str):
        """
        Reads the csv files, loads the data into memory, and prepares it
        csv files are similar in structure to the sustainable competition database
        self.data has
        - one column per hash,
        - one column per instance/environment/solver feature,
        - one for the performance and
        - one for the exit status of the solver

        Raises:
            FileNotFoundError: if csv files are not there
        """
        # Load features
        self.environments = pl.read_csv(environments_path)
        self.instances = pl.read_csv(instances_path)
        self.solvers = pl.read_csv(solvers_path)
        # Load performances
        self.perfs = pl.read_csv(performances_path)
        # Merge perf with environments on env_id
        self.data = self.perfs.join(self.environments, left_on="env_id", right_on="env_id", how="left")

        # Merge with instances on inst_hash
        self.data = self.data.join(self.instances, left_on="inst_hash", right_on="inst_hash", how="left")

        # Merge with solvers on solver_id
        self.data = self.data.join(self.solvers, left_on="solver_id", right_on="solver_id", how="left")

    def get_performances(
        self, inst_hash: Optional[str] = None, solver_id: Optional[str] = None, env_id: Optional[str] = None, filter: Optional[str] = None
    ) -> pl.DataFrame:
        """Get as a data frame all performances for the specified inst_hash, solver_id and env_id.
        If none are specified, returns all the data


        Args:
            inst_hash (str, optional): the id of the instance to get the performances about
            solver_id (str, optional): If set, only gives the performance with the specified id. Defaults to None.
            env_id (str, optional): If set, only gives the performance with the specified id. Defaults to None.

        Returns:
            pl.DataFrame: _description_
        """
        result = self.data

        if inst_hash:
            result = result.filter(pl.col("inst_hash") == inst_hash)

        if solver_id:
            result = result.filter(pl.col("solver_id") == solver_id)

        if env_id:
            result = result.filter(pl.col("hardware_hash") == env_id)

        return result

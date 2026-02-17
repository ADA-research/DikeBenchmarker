"""
Competition data adaptor to interact with the competition data from a single competition.
The data from a single competition is typically served as a CSV file.
It stems from benchmarking with a single hardware configuration.
"""

from typing import Optional

import polars as pl

from sustainablecompetition.dataadaptors.dataadaptor import DataAdaptor
from sustainablecompetition.dataadaptors.sqlite_dataadaptor import SqlDataAdaptor


__all__ = ["CompetitionDataAdaptor"]


class CompetitionDataAdaptor(DataAdaptor):
    """
    Implement the data adaptor for competition data.
    """

    competition_environment = {"main2024": "b7ad30888a207d186290d1b584d32ed6"}

    def __init__(self, df: str = None, csv: str = None, source_name: str = None, database_path: str = None):
        """Initialize the data adaptor with a polars DataFrame or a csv
        Args:
            df (pl.DataFrame): DataFrame containing the competition data.
            The DataFrame must contain at least the following columns:
                - hash: the id of the benchmark instance
                - other columns names are the ids of the solvers
            csv (str): csv file containing the competition data.
            The DataFrame must contain at least the following columns:
                - hash: the id of the benchmark instance
                - other columns names are the ids of the solvers
            source_name (str): the name of the competition to allow for meta data retrieval
            database_path (str): the path of the sustainable competition database to allow for meta data retrieval
        """
        if df is not None:
            self.data = df.rename({"hash": "inst_hash"})
        elif csv:
            self.data = pl.read_csv(csv).rename({"hash": "inst_hash"})

        self.prepare_data(source_name, database_path)

    @classmethod
    def from_dataframe(cls, df: pl.DataFrame, source_name: str = None, database_path: str = None):
        """
        Initialize the data adaptor with a polars DataFrame.
        Args:
            df (pl.DataFrame): DataFrame containing the competition data.
            The DataFrame must contain at least the following columns:
                - hash: the id of the benchmark instance
                - other columns names are the ids of the solvers
            source_name (str): the name of the competition to allow for meta data retrieval
            database_path (str): the path of the sustainable competition database to allow for meta data retrieval
        """
        return cls(df, None, source_name, database_path)

    @classmethod
    def from_competition_csv(cls, competition_data: str, source_name: str = None, database_path: str = None):
        """
        Initialize the data adaptor with the corresponding csv data from the sat competition website
        following recent competition format (since 2021)
        Args:
            competition_data (str): csv file containing the competition data.
            The DataFrame must contain at least the following columns:
                - hash: the id of the benchmark instance
                - other columns names are the ids of the solvers
            source_name (str): the name of the competition to allow for meta data retrieval
            database_path (str): the path of the sustainable competition database to allow for meta data retrieval
        """
        return cls(None, competition_data, source_name, database_path)

    def prepare_data(self, source_name: str = None, database_path: str = None):
        """pivot data and use our database for getting the environment, instances and solver features
        Args:
            source_name (str): the name of the competition to allow for meta data retrieval
            database_path (str): the path of the sustainable competition database to allow for meta data retrieval
        """
        # Melt the DataFrame to long format
        df_long = self.data.unpivot(index="inst_hash", variable_name="solver_name", value_name="perf")

        # Connect to database
        if database_path and source_name:
            db_adaptor = SqlDataAdaptor(database_path)
            env_id, res_id = db_adaptor.get_competition_env(source_name)
        else:
            db_adaptor = None
            env_id = None
            res_id = None

        # Map solver_name to solver_id
        if db_adaptor:
            df_long = df_long.with_columns(
                pl.col("solver_name")
                .map_elements(lambda name: db_adaptor.get_competition_solver_id(source_name, name), return_dtype=pl.String)
                .alias("solver_id")
            )
        else:
            df_long = df_long.with_columns(pl.col("solver_name").map_elements(lambda name: f"{name}", return_dtype=pl.String).alias("solver_id"))

        # Set env_id
        if env_id is None:
            env_id = "unknown_env"
        df_long = df_long.with_columns(env_id=pl.lit(env_id))

        # Set res_id
        if res_id is None:
            res_id = "unknown_res"
        df_long = df_long.with_columns(res_id=pl.lit(res_id))

        # Determine status
        df_long = df_long.with_columns(pl.when(pl.col("perf") == 10000).then(pl.lit("TIMEOUT")).otherwise(pl.lit("COMPLETE")).alias("status"))

        # format and set perf dataframe
        self.perfs = df_long.select(["status", "perf", "inst_hash", "env_id", "res_id", "solver_id"])

        # Load features using db_adaptor
        if db_adaptor is not None:
            self.environments = db_adaptor.get_environments(env_ids=[env_id])
            self.resources = db_adaptor.get_resources(res_ids=[res_id])
            self.instances = db_adaptor.get_instances(inst_ids=list(self.perfs["inst_hash"]))
            self.solvers = db_adaptor.get_solvers(solver_ids=list(self.perfs["solver_id"]))
            # Merge perf with environments on env_id
            self.data = self.perfs.join(self.environments, left_on="env_id", right_on="env_id", how="left")

            # Merge with resources on res_id
            self.data = self.data.join(self.resources, left_on="res_id", right_on="res_id", how="left")

            # Merge with instances on inst_hash
            self.data = self.data.join(self.instances, left_on="inst_hash", right_on="inst_hash", how="left")

            # Merge with solvers on solver_id
            self.data = self.data.join(self.solvers, left_on="solver_id", right_on="solver_id", how="left")
        else:
            self.data = self.perfs

    def get_performances(
        self, inst_hash: Optional[str] = None, solver_id: Optional[str] = None, env_id: Optional[str] = None, filter: Optional[str] = None
    ) -> pl.DataFrame:
        """
        Get the performance of a specific benchmark instance.
        Hardware id is ignored as this data adaptor is for a single hardware configuration. (TODO: find a better way to handle this)
        Args:
            inst_hash (str): the id of the instance to get the performances about
            solver_id (Optional[str], optional): If set, only gives the performance with the specified id. Defaults to None.
        """
        result = self.data

        if inst_hash:
            result = result.filter(pl.col("inst_hash") == inst_hash)

        if solver_id:
            result = result.filter(pl.col("solver_id") == solver_id)

        if env_id:
            result = result.filter(pl.col("env_id") == env_id)

        return result

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
            database_path (str): the path of the sustainable competiiton database to allow for meta data retrieval
        """
        if df:
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
            database_path (str): the path of the sustainable competiiton database to allow for meta data retrieval
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
            database_path (str): the path of the sustainable competiiton database to allow for meta data retrieval
        """
        return cls(None, competition_data, source_name, database_path)

    def prepare_data(self, source_name: str = None, database_path: str = None):
        """pivot data and use our database for getting the environment, instances and solver features
        Args:
            source_name (str): the name of the competition to allow for meta data retrieval
            database_path (str): the path of the sustainable competiiton database to allow for meta data retrieval
        """
        # - comp_name is the competition name
        # - get_competition_env_hash and get_solver are defined elsewhere

        # Melt the DataFrame to long format
        df_long = self.data.melt(
            id_vars=["inst_hash"], value_vars=[col for col in self.data.columns if col != "inst_hash"], var_name="solver_name", value_name="perf"
        )

        # Connect to database
        if database_path and source_name:
            db_adaptor = SqlDataAdaptor(database_path)
            env_hash = db_adaptor.get_competition_env_hash(source_name)

        # Map solver_name to solver_hash
        if db_adaptor:
            df_long = df_long.with_columns(pl.col("solver_name").map_elements(lambda name: db_adaptor.get_solver(source_name, name)).alias("solver_hash"))
        else:
            df_long = df_long.with_columns(pl.col("solver_name").map_elements(lambda name: f"unknown_solver_{name}").alias("solver_hash"))

        # Set env_hash
        if not env_hash:
            env_hash = "unknown_env"

        # Determine status
        df_long = df_long.with_columns(pl.when(pl.col("perf") == 10000).then("TIMEOUT").otherwise("COMPLETE").alias("status"))

        # format and set perf dataframe
        self.perfs = df_long.select(["status", "perf", "inst_hash", "env_hash", "solver_hash"])

        # Load features using db_adaptor
        if db_adaptor:
            self.environments = db_adaptor.get_environments(env_ids=[env_hash])
            self.instances = db_adaptor.get_instances(inst_ids=list(self.perfs["inst_hash"]))
            self.solvers = db_adaptor.get_solvers(solver_ids=list(self.perfs["solver_hash"]))

    def get_performances(self, benchmark_id: str, solver_id: Optional[str] = None, hardware_id: Optional[str] = None) -> pl.DataFrame:
        """
        Get the performance of a specific benchmark instance.
        Hardware id is ignored as this data adaptor is for a single hardware configuration. (TODO: find a better way to handle this)
        Args:
            benchmark_id (str): the id of the instance to get the performances about
            solver_id (Optional[str], optional): If set, only gives the performance with the specified id. Defaults to None.
        """
        result = self.data

        if benchmark_id:
            result = result.filter(pl.col("inst_hash") == benchmark_id)

        if solver_id:
            result = result.filter(pl.col("solver_hash") == solver_id)

        if hardware_id:
            result = result.filter(pl.col("hardware_hash") == hardware_id)

        return result

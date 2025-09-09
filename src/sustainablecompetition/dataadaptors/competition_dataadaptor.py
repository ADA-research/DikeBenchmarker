"""
Competition data adaptor to interact with the competition data from a single competition.
The data from a single competition is typically served as a CSV file.
It stems from benchmarking with a single hardware configuration.
"""

from typing import Optional

import polars as pl

from sustainablecompetition.dataadaptors.dataadaptor import DataAdaptor


__all__ = ["CompetitionDataAdaptor"]


class CompetitionDataAdaptor(DataAdaptor):
    """
    Implement the data adaptor for competition data.
    """

    competition_environment = {"main2024": "b7ad30888a207d186290d1b584d32ed6"}

    def __init__(self, df=None, csv=None):
        """Initialize the data adaptor with a polars DataFrame or a csv
        Args:
            df (pl.DataFrame): DataFrame containing the competition data.
            The DataFrame must contain at least the following columns:
                - hash: the id of the benchmark instance
                - other columns names are the ids of the solvers
        """
        if df:
            self.data = df
        elif csv:
            self.data = pl.read_csv(csv)

        self.prepare_data()

    @classmethod
    def from_dataframe(cls, df: pl.DataFrame):
        """
        Initialize the data adaptor with a polars DataFrame.
        Args:
            df (pl.DataFrame): DataFrame containing the competition data.
            The DataFrame must contain at least the following columns:
                - hash: the id of the benchmark instance
                - other columns names are the ids of the solvers
        """
        return cls(df, None)

    @classmethod
    def from_competition_csv(cls, competition_data: str):
        """
        Initialize the data adaptor with the corresponding csv data from the sat competition website
        following recent competition format (since 2021)
        Args:
            competition_data (str): csv file containing the competition data.
            The DataFrame must contain at least the following columns:
                - hash: the id of the benchmark instance
                - other columns names are the ids of the solvers
        """
        return cls(None, competition_data)

    def prepare_data(self):
        """pivot data and use our database for getting the environment, instances and solver features
        TODO
        """
        pass

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

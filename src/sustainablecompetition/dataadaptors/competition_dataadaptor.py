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

    def __init__(self, df: pl.DataFrame):
        """
        Initialize the data adaptor with a polars DataFrame.
        Args:
            df (pl.DataFrame): DataFrame containing the competition data.
            The DataFrame must contain at least the following columns:
                - hash: the id of the benchmark instance
                - other columns: the ids of the solvers
        """
        self.df = df

    def get_performances(self, benchmark_id: str, solver_id: Optional[str] = None, hardware_id: Optional[str] = None) -> pl.DataFrame:
        """
        Get the performance of a specific benchmark instance.
        Hardware id is ignored as this data adaptor is for a single hardware configuration. (TODO: find a better way to handle this)
        Args:
            benchmark_id (str): the id of the instance to get the performances about
            solver_id (Optional[str], optional): If set, only gives the performance with the specified id. Defaults to None.
        """
        if solver_id is not None:
            return self.df.filter(pl.col("hash") == benchmark_id).select(solver_id)
        return self.df.filter(pl.col("hash") == benchmark_id)

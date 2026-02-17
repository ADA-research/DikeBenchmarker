from abc import ABC, abstractmethod
from typing import Optional


import polars as pl


__all__ = ["DataAdaptor"]


class DataAdaptor(ABC):
    """
    Enables to interact with the data interactively without loading everything into memory.
    """

    @abstractmethod
    def get_performances(self, inst_hash: str, solver_id: Optional[str] = None, env_id: Optional[str] = None, filter: Optional[str] = None) -> pl.DataFrame:
        """Get as a data frame all performances for the specific inst_hash.


        Args:
            inst_hash (str): the id of the instance to get the performances about
            solver_id (Optional[str], optional): If set, only gives the performance with the specified id. Defaults to None.
            env_id (Optional[str], optional): If set, only gives the performance with the specified id. Defaults to None.

        Returns:
            pl.DataFrame: _description_
        """
        pass

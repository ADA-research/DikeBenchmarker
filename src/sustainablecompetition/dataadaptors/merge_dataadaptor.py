from typing import Optional


import polars as pl

from sustainablecompetition.dataadaptors.dataadaptor import DataAdaptor


__all__ = ["MergeDataAdaptor"]


class MergeDataAdaptor(DataAdaptor):
    """Merge the data from multiple data adaptors.

    Duplicated data is duplicated.

    """

    def __init__(self, data_adaptors: list[DataAdaptor]):
        super().__init__()
        self.data_adaptors = data_adaptors

    def get_performances(self, inst_hash: str, solver_id: Optional[str] = None, env_id: Optional[str] = None, filter: Optional[str] = None) -> pl.DataFrame:
        dfs = [d.get_performances(inst_hash, solver_id, env_id, filter).j for d in self.data_adaptors]
        df: pl.DataFrame = dfs.pop()
        for el in dfs:
            # df = df.join(el, how="full", coalesce=True)
            df = df.merge_sorted(el, "inst_hash")

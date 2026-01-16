"""
CSV consumer for benchmarking results.
"""

import os
import polars as pl

from sustainablecompetition.benchmarkatoms import Result
from sustainablecompetition.resultconsumers.abstract_consumer import AbstractConsumer

__all__ = ["CSVConsumer"]


class CSVConsumer(AbstractConsumer):
    """Writes the result to a CSV file."""

    def __init__(self, csv_path: str):
        super().__init__()
        self.csv_path = csv_path

        if os.path.exists(csv_path):
            df = pl.read_csv(csv_path)
            if not {"inst_hash", "solver_hash", "perf"}.issubset(df.columns):
                raise ValueError("csv exists and has wrong format")
            self.df = df
        else:
            self.df = pl.DataFrame(schema={"inst_hash": pl.Utf8, "solver_hash": pl.Utf8, "perf": pl.Utf8})
            self.df.write_csv(csv_path)

    def consume_result(self, result: Result):
        row = {"inst_hash": result.job.benchmark_id, "solver_hash": result.job.solver_id, "perf": result.runtime}
        new_row = pl.DataFrame([row])
        self.df = pl.concat([self.df, new_row], how="vertical")
        self.df.write_csv(self.csv_path)

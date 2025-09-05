import polars as pl

from sustainablecompetition.dataadaptors.dataadaptor import DataAdaptor


__all__ = ["CsvDataAdaptor"]


class CsvDataAdaptor(DataAdaptor):
    """
    Implement the data adaptor for competition data.
    """

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

    def get_performances(self, environments_path, instances_path, solvers_path, performances_path):
        """Reads the csv files, loads the data into memory, and prepare it

        Raises:
            FileNotFoundError: if csv files are not there
        """
        # Load features
        self.environments = pl.read_csv(environments_path)
        self.instances = pl.read_csv(instances_path)
        self.solvers = pl.read_csv(solvers_path)
        # Load performances
        self.perf = pl.read_csv(performances_path)
        # Merge perf with environments on env_hash
        self.df = self.perf.join(self.environments, left_on="env_hash", right_on="env_hash", how="left")

        # Merge with instances on inst_hash
        self.df = self.df.join(self.instances, left_on="inst_hash", right_on="inst_hash", how="left")

        # Merge with solvers on solver_hash
        self.df = self.df.join(self.solvers, left_on="solver_hash", right_on="solver_hash", how="left")

        return self.df

import polars as pl

from sustainablecompetition.dataadaptors.dataadaptor import DataAdaptor


__all__ = ["CsvDataAdaptor"]


class CsvDataAdaptor(DataAdaptor):
    """
    Implement the data adaptor for competition data.
    """

    def __init__(self, environments_path, instances_path, solvers_path, performances_path):
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
        self.perf = pl.read_csv(performances_path)
        # Merge perf with environments on env_hash
        self.data = self.perf.join(self.environments, left_on="env_hash", right_on="env_hash", how="left")

        # Merge with instances on inst_hash
        self.data = self.data.join(self.instances, left_on="inst_hash", right_on="inst_hash", how="left")

        # Merge with solvers on solver_hash
        self.data = self.data.join(self.solvers, left_on="solver_hash", right_on="solver_hash", how="left")

    def get_performances(self, benchmark_id: str = None, solver_id: str = None, hardware_id: str = None) -> pl.DataFrame:
        """Get as a data frame all performances for the specified benchmark_id, solver_id and hardware_id.
        If none are specified, returns all the data


        Args:
            benchmark_id (str, optional): the id of the instance to get the performances about
            solver_id (str, optional): If set, only gives the performance with the specified id. Defaults to None.
            hardware_id (str, optional): If set, only gives the performance with the specified id. Defaults to None.

        Returns:
            pl.DataFrame: _description_
        """
        result = self.data

        if benchmark_id:
            result = result.filter(pl.col("inst_hash") == benchmark_id)

        if solver_id:
            result = result.filter(pl.col("solver_hash") == solver_id)

        if hardware_id:
            result = result.filter(pl.col("hardware_hash") == hardware_id)

        return result
            

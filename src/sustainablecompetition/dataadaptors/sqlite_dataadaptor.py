import polars as pl
import sqlite3
from typing import Optional

import polars as pl

from sustainablecompetition.dataadaptors.dataadaptor import DataAdaptor


__all__ = ["SqlDataAdaptor"]


class SqlDataAdaptor(DataAdaptor):
    """
    Implement the data adaptor for sqlite data.
    """

    def __init__(self, database_path: str):
        """
        Reads the database from sustainablecompetition package
        """

        self.database_path = database_path

    def get_performances(
        self, inst_hash: Optional[str] = None, solver_hash: Optional[str] = None, env_hash: Optional[str] = None, filter: Optional[str] = None) -> pl.DataFrame:
        """
        Get as a DataFrame all performances for the specified inst_hash, solver_hash, and env_hash.
        If none are specified, returns all the data (not recommended).

        Args:
            inst_hash (str, optional): The id of the instance (inst_hash) to get the performances about.
            solver_hash (str, optional): If set, only gives the performance with the specified solver_hash. Defaults to None.
            env_hash (str, optional): If set, only gives the performance with the specified env_hash. Defaults to None.
            filter (str): can contain 'no_inst_features' | 'no_env_features' | 'no_solver_features' to omit the features of one aspect

        Returns:
            pl.DataFrame: A DataFrame containing the performances.
        """
        # Connect to the SQLite database (replace 'your_database.db' with your actual database file)
        conn = sqlite3.connect(self.database_path)
        
        try:
            # Base query
            query = (
                "SELECT p.perf, p.status,"
                + f"{'e.env_hash' if filter == 'no_env_features' else 'e.*'},"
                + f"{'i.inst_hash' if filter == 'no_inst_features' else 'i.*'},"
                + f"{'s.solver_hash' if filter == 'no_solver_features' else 's.*'}"
                + """
                FROM performances p
                LEFT JOIN environments e ON p.env_hash = e.env_hash
                LEFT JOIN instances i ON p.inst_hash = i.inst_hash
                LEFT JOIN solvers s ON p.solver_hash = s.solver_hash
            """
            )

            # List to hold conditions and parameters
            conditions = []
            params = []

            if inst_hash is not None:
                conditions.append("p.inst_hash = ?")
                params.append(inst_hash)
            if solver_hash is not None:
                conditions.append("p.solver_hash = ?")
                params.append(solver_hash)
            if env_hash is not None:
                conditions.append("p.env_hash = ?")
                params.append(env_hash)

            if conditions:
                query += " WHERE " + " AND ".join(conditions)

            # Execute the query with parameters
            df = pl.read_database(query, conn, execute_options={"parameters": params})
            return df
        finally:
            conn.close()

    def get_competition_env_hash(self, comp_name: str):
        """
        Returns the hash of the environment used during the given competition.

        Args:
            comp_name (str): Name of the competition track.

        Returns:
            Optional[str]: The environment hash, or None if not found.
        """
        conn = sqlite3.connect(self.database_path)
        try:
            cursor = conn.cursor()
            # Use parameterized query to avoid SQL injection
            query = "SELECT env_hash FROM competition_compatibility WHERE competition = ?"
            cursor.execute(query, (comp_name,))
            result = cursor.fetchone()
            return result[0] if result else None
        finally:
            conn.close()

    def get_competition_solver_hash(self, comp_name: str, solver_name: Optional[str] = None):
        """
        Get the solver hash corresponding to the given solver name during the given competition.
        If no solver name is given, returns a list of all solver hashes from the competition.

        Args:
            comp_name (str): Name of the competition.
            solver_name (Optional[str]): Name of the solver. If None, returns all solver hashes.

        Returns:
            Union[str, List[str], None]: Solver hash, list of solver hashes, or None if not found.
        """

        conn = sqlite3.connect(self.database_path)
        try:
            cursor = conn.cursor()
            if solver_name:
                # Fetch the solver hash for the given solver name and competition
                query = """
                    SELECT solver_hash
                    FROM solvers
                    WHERE competition = ? AND solver_name = ?
                """
                cursor.execute(query, (comp_name, solver_name))
                result = cursor.fetchone()
                return result[0] if result else None
            else:
                # Fetch all solver hashes for the competition
                query = """
                    SELECT solver_hash
                    FROM solvers
                    WHERE competition = ?
                """
                cursor.execute(query, (comp_name,))
                results = cursor.fetchall()
                return [row[0] for row in results] if results else []
        finally:
            conn.close()

    def get_environments(self, env_ids: list) -> pl.DataFrame:
        """
        Returns the full environment rows for the given environment IDs.

        Args:
            env_ids: List of environment hashes.

        Returns:
            pl.DataFrame: DataFrame containing the environment rows.
        """
        conn = sqlite3.connect(self.database_path)
        try:
            query = """
                SELECT *
                FROM environments
                WHERE env_hash IN (?{})
            """.format(",?" * (len(env_ids) - 1))  # Parameterize for all env_ids
            return pl.read_database(query, conn, execute_options={"parameters": env_ids})
        finally:
            conn.close()

    def get_instances(self, inst_ids: list) -> pl.DataFrame:
        """
        Returns the full instance rows for the given instance IDs.

        Args:
            inst_ids: List of instance hashes.

        Returns:
            pl.DataFrame: DataFrame containing the instance rows.
        """
        conn = sqlite3.connect(self.database_path)
        try:
            query = """
                SELECT *
                FROM instances
                WHERE inst_hash IN (?{})
            """.format(",?" * (len(inst_ids) - 1))  # Parameterize for all inst_ids
            return pl.read_database(query, conn, execute_options={"parameters": inst_ids})
        finally:
            conn.close()

    def get_solvers(self, solver_hashs: list) -> pl.DataFrame:
        """
        Returns the full solver rows for the given solver IDs.

        Args:
            solver_hashs: List of solver hashes.

        Returns:
            pl.DataFrame: DataFrame containing the solver rows.
        """
        conn = sqlite3.connect(self.database_path)
        try:
            query = """
                SELECT *
                FROM solvers
                WHERE solver_hash IN (?{})
            """.format(",?" * (len(solver_hashs) - 1))  # Parameterize for all solver_hashs
            return pl.read_database(query, conn, execute_options={"parameters": solver_hashs})
        finally:
            conn.close()

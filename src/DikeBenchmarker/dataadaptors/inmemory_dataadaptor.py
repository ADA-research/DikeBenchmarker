"""In-memory DataAdaptor backed by a preloaded performance dict."""

import polars as pl
from typing import Optional

from DikeBenchmarker.dataadaptors.dataadaptor import DataAdaptor

__all__ = ["InMemoryDataAdaptor"]


class InMemoryDataAdaptor(DataAdaptor):
    """DataAdaptor backed by a preloaded dict for fast in-memory lookups.

    Replaces per-call SQLite queries with simple dict lookups.  Intended
    for use when all required (inst_hash, solver_id) pairs are known
    upfront and can be bulk-loaded once before spawning worker processes.
    """

    def __init__(self, perf_lookup: dict):
        """
        Args:
            perf_lookup: dict mapping (inst_hash, solver_id) -> float perf value.
        """
        self._lookup = perf_lookup
        # Index by inst_hash for queries without a solver_id filter.
        self._by_inst: dict[str, list[float]] = {}
        for (inst_hash, _solver_id), perf in perf_lookup.items():
            self._by_inst.setdefault(inst_hash, []).append(perf)

    def get_performances(
        self,
        inst_hash: Optional[str] = None,
        solver_id: Optional[str] = None,
        env_id: Optional[str] = None,
        res_id: Optional[int] = None,
        filter: Optional[str] = None,
    ) -> pl.DataFrame:
        if inst_hash is not None and solver_id is not None:
            perf = self._lookup.get((inst_hash, solver_id))
            if perf is None:
                return pl.DataFrame({"perf": pl.Series([], dtype=pl.Float64)})
            return pl.DataFrame({"perf": [perf]})
        elif inst_hash is not None:
            perfs = self._by_inst.get(inst_hash, [])
            return pl.DataFrame({"perf": pl.Series(perfs, dtype=pl.Float64)})
        elif solver_id is not None:
            perfs = [v for (i, s), v in self._lookup.items() if s == solver_id]
            return pl.DataFrame({"perf": pl.Series(perfs, dtype=pl.Float64)})
        else:
            return pl.DataFrame({"perf": pl.Series(list(self._lookup.values()), dtype=pl.Float64)})

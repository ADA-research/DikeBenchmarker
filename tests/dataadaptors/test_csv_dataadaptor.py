import pytest
from sustainablecompetition.dataadaptors.csv_dataadaptor import CsvDataAdaptor


INSTANCE_HASH = "b4f28bc5f78ead2bf150639790768df4"

ALL_COLS = [
    "L1",
    "L2",
    "L3",
    "OS",
    "activated_modules",
    "assigned_memory",
    "balancecls_entropy",
    "balancecls_max",
    "balancecls_mean",
    "balancecls_min",
    "balancecls_variance",
    "balancevars_entropy",
    "balancevars_max",
    "balancevars_mean",
    "balancevars_min",
    "balancevars_variance",
    "base_features_runtime",
    "bytes",
    "ccs",
    "cg_degree_entropy",
    "cg_degree_max",
    "cg_degree_mean",
    "cg_degree_min",
    "cg_degree_variance",
    "clauses",
    "cls1",
    "cls10p",
    "cls2",
    "cls3",
    "cls4",
    "cls5",
    "cls6",
    "cls7",
    "cls8",
    "cls9",
    "cpu_boost",
    "cpu_brand",
    "cpu_freq",
    "cpu_model",
    "env_hash",
    "horn",
    "hornvars_entropy",
    "hornvars_max",
    "hornvars_mean",
    "hornvars_min",
    "hornvars_variance",
    "inst_hash",
    "invhorn",
    "invhornvars_entropy",
    "invhornvars_max",
    "invhornvars_mean",
    "invhornvars_min",
    "invhornvars_variance",
    "kernel_version",
    "machine_memory",
    "nb_assigned_cores",
    "nb_available_core",
    "negative",
    "perf",
    "positive",
    "solver_base",
    "solver_hash",
    "solver_name",
    "status",
    "variables",
    "vcg_cdegree_entropy",
    "vcg_cdegree_max",
    "vcg_cdegree_mean",
    "vcg_cdegree_min",
    "vcg_cdegree_variance",
    "vcg_vdegree_entropy",
    "vcg_vdegree_max",
    "vcg_vdegree_mean",
    "vcg_vdegree_min",
    "vcg_vdegree_variance",
    "version",
    "vg_degree_entropy",
    "vg_degree_max",
    "vg_degree_mean",
    "vg_degree_min",
    "vg_degree_variance",
]


def build_adaptor() -> CsvDataAdaptor:
    folder = "./examples/dataAdaptors"
    return CsvDataAdaptor(f"{folder}/environments.csv", f"{folder}/instances.csv", f"{folder}/solvers.csv", f"{folder}/performances.csv")


@pytest.mark.dependency()
def test_load():
    adaptor = build_adaptor()


@pytest.mark.dependency(depends=["test_load"])
def test_get_perf():
    adaptor = build_adaptor()
    perf = adaptor.get_performances(INSTANCE_HASH)
    assert sorted(perf.columns) == ALL_COLS

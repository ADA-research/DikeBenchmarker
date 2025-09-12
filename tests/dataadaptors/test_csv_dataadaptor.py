import pytest
from sustainablecompetition.dataadaptors.csv_dataadaptor import CsvDataAdaptor


INSTANCE_HASH = "b4f28bc5f78ead2bf150639790768df4"

ALL_COLS = [
    "env_hash",
    "nb_assigned_cores",
    "assigned_memory",
    "nb_available_core",
    "machine_memory",
    "OS",
    "kernel_version",
    "min_cpu_freq",
    "max_cpu_freq",
    "arch",
    "cpu_brand",
    "cpu_model",
    "l1_instruction_cache_size",
    "l1_data_cache_size",
    "l2_cache_size",
    "l2_cache_line_size",
    "l2_cache_associativity",
    "l3_cache_size",
    "inst_hash",
    "base_features_runtime",
    "clauses",
    "variables",
    "cls1",
    "cls2",
    "cls3",
    "cls4",
    "cls5",
    "cls6",
    "cls7",
    "cls8",
    "cls9",
    "cls10p",
    "horn",
    "invhorn",
    "positive",
    "negative",
    "hornvars_mean",
    "hornvars_variance",
    "hornvars_min",
    "hornvars_max",
    "hornvars_entropy",
    "invhornvars_mean",
    "invhornvars_variance",
    "invhornvars_min",
    "invhornvars_max",
    "invhornvars_entropy",
    "balancecls_mean",
    "balancecls_variance",
    "balancecls_min",
    "balancecls_max",
    "balancecls_entropy",
    "balancevars_mean",
    "balancevars_variance",
    "balancevars_min",
    "balancevars_max",
    "balancevars_entropy",
    "vcg_vdegree_mean",
    "vcg_vdegree_variance",
    "vcg_vdegree_min",
    "vcg_vdegree_max",
    "vcg_vdegree_entropy",
    "vcg_cdegree_mean",
    "vcg_cdegree_variance",
    "vcg_cdegree_min",
    "vcg_cdegree_max",
    "vcg_cdegree_entropy",
    "vg_degree_mean",
    "vg_degree_variance",
    "vg_degree_min",
    "vg_degree_max",
    "vg_degree_entropy",
    "cg_degree_mean",
    "cg_degree_variance",
    "cg_degree_min",
    "cg_degree_max",
    "cg_degree_entropy",
    "bytes",
    "ccs",
    "solver_hash",
    "solver_name",
    "solver_base",
    "competition",
    "status",
    "perf",
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
    print(set(perf.columns).difference(set(ALL_COLS)))
    assert sorted(perf.columns) == sorted(ALL_COLS)

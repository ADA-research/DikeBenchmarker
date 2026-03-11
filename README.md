# DikeBenchmarker

## Data-Informed Knowledge-driven Evaluation for Sustainable Solver Competitions

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/github/license/ADA-research/DikeBenchmarker)](LICENSE)
[![Documentation](https://img.shields.io/badge/docs-Sphinx-blue)](https://ada-research.github.io/DikeBenchmarker)

---

## Table of Contents

- [Overview](#overview)
- [Motivation](#motivation)
- [Architecture](#architecture)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Core Concepts](#core-concepts)
  - [Instance Selectors](#instance-selectors)
  - [Stopping Criteria](#stopping-criteria)
  - [Data Adaptors](#data-adaptors)
  - [Infrastructure Runners](#infrastructure-runners)
  - [Result Consumers](#result-consumers)
- [Code Examples](#code-examples)
- [Configuration File Reference](#configuration-file-reference)
- [Documentation](#documentation)
- [Contributing](#contributing)
- [Citing](#citing)

---

## Overview

DikeBenchmarker is a Python framework for conducting **sustainable solver competitions**. Instead of evaluating every solver on every benchmark instance—a combinatorial bottleneck in large-scale competitions—DikeBenchmarker intelligently selects which instances to run and when to stop, while preserving statistical confidence in the final solver ranking.

The framework is designed around the following principles:

- **Modularity**: All components (instance selectors, stopping criteria, data adaptors, infrastructure runners) are interchangeable via clean abstract interfaces.
- **Sustainability**: Dramatically reduce total CPU-hours consumed by solver competitions without sacrificing ranking accuracy.
- **Statistical rigor**: Stopping decisions are grounded in non-parametric statistical tests (Wilcoxon signed-rank) and information-theoretic criteria.
- **Scalability**: Native support for both local multi-process execution and distributed SLURM cluster execution via [Parsl](https://parsl-project.org/).

The project is developed by the [ADA Research Group](https://github.com/ADA-research) and targets the SAT competition community, though the architecture generalises to any solver benchmarking domain.

---

## Motivation

Modern solver competitions (e.g., the SAT Competition) evaluate dozens of solvers across thousands of benchmark instances, consuming millions of CPU-hours. The key observation motivating DikeBenchmarker is:

> **Not all instances are equally informative.** Many instances are trivially solved by every solver, while a small subset of *discriminating* instances carry the majority of the information needed to rank solvers.

DikeBenchmarker exploits historical performance data to:

1. **Rank instances** by their expected discriminating power (discrimination-based or variance-based selection).
2. **Adapt stopping** once sufficient statistical confidence in the ranking has been achieved (Wilcoxon test, minimum accuracy, or a fixed percentage).
3. **Reduce cost** by skipping redundant evaluations without distorting the competition ranking.

The result is a benchmarking loop that runs only as many solver–instance pairs as are necessary to produce a reliable ranking, potentially reducing competition cost by an order of magnitude.


**Job lifecycle:**

```
CREATED ──► SUBMITTED ──► RUNNING ──► FINISHED
                │                 └──► FAILED
                └──────────────────► CANCELLED
```

---

## Installation

### With the SQLite Database (recommended)

The repository ships a bundled SQLite database containing historical SAT competition performance data. To restore it:

1. Clone the repository **with submodules**:

   ```bash
   git clone --recurse-submodules https://github.com/ADA-research/DikeBenchmarker.git
   cd DikeBenchmarker
   ```

2. Ensure `sqlite3` is available on your system:

   ```bash
   sqlite3 --version
   ```

3. Run the setup script to configure git filters and restore the database:

   ```bash
   cd src/DikeBenchmarker/data/db
   ./setup.sh
   cd ../../../..
   ```

4. The database will be automatically restored from the SQL dump.

5. Install the package (using [uv](https://docs.astral.sh/uv/) or pip):

   ```bash
   # with uv (recommended)
   uv sync

   # or with pip
   pip install -e .
   ```

### Without the Database

If you prefer to work from your own data files or from data originating from [GBD](https://benchmark-database.de/), submodules are not required:

```bash
git clone https://github.com/ADA-research/DikeBenchmarker.git
cd DikeBenchmarker
pip install -e .
```

### Developer Installation

```bash
git clone --recurse-submodules https://github.com/ADA-research/DikeBenchmarker.git
cd DikeBenchmarker
uv sync --group dev
```

This installs additional dependencies for testing (`pytest`, `pytest-dependency`) and linting (`ruff`).

---

## Quick Start

The minimal example below benchmarks a new solver against a SAT competition field using random instance selection and a Wilcoxon-based stopping criterion:

```python
import importlib.resources
from DikeBenchmarker.benchmarkadaptors.satinstance import SATInstanceAdaptor
from DikeBenchmarker.benchmarkingmethods.benchmarker import Benchmarker
from DikeBenchmarker.benchmarkingmethods.instance_selectors.random_instance_selector import RandomInstanceSelector
from DikeBenchmarker.benchmarkingmethods.stopping_criterion.wilcoxon_stopping_criterion import WilcoxonStoppingCriterion
from DikeBenchmarker.dataadaptors.sqlite_dataadaptor import SqlDataAdaptor
from DikeBenchmarker.infrastructureadaptors.local_runner import LocalRunner
from DikeBenchmarker.solveradaptors.solveradaptor import SolverAdaptor

ccompetition = "main2024"
solver_id = "my_solver_id"
confidence = 0.95
# Load prior data from existing database
adap = SqlDataAdaptor("my_db.db")

# Load prior data from database (here a competition)
solvers_challenged = adap.get_competition_solver_id(competition)
benchmark_ids = adap.get_competition_instance_id(competition)
# Create benchmarking method
benchmarker = Benchmarker(
        RandomInstanceSelector(benchmark_ids, solver_id, seed=1),
        WilcoxonStoppingCriterion(benchmark_ids, solver_id,
                solvers_challenged, confidence, adap),
        benchmark_ids,
        solver_id)
# Load files locally
solver_adaptor = SolverAdaptor()
solver_adaptor.read_registry("./solvers/sat/")
instance_adaptor = SATInstanceAdaptor("./instances/sat/",
        "./instances/cnf_data.db")
# Now make a runner so that we actually run something
runner = LocalRunner(solver_adaptor, instance_adaptor, parallel=1)
runner.run([benchmarker])
```

---

## Core Concepts

### Instance Selectors

An `InstanceSelector` determines the **order** in which benchmark instances are presented to the solver. All selectors implement the `InstanceSelector` abstract base class and expose:

- `next_benchmark_id() → str` — return the next instance hash to run
- `handle_result(result: Result) → None` — update internal state after a result arrives

| Selector | Key Idea | When to Use |
| --- | --- | --- |
| `TrivialInstanceSelector` | Sequential, all instances | Baseline / allpairs mode |
| `RandomInstanceSelector` | Randomly shuffled (optional seed) | Unbiased baselines |
| `DiscriminationInstanceSelector` | Prioritises instances with high discrimination score ρ | Historical data available |
| `VarianceInstanceSelector` | Prioritises instances with high variance-to-mean runtime ratio | Historical data available |

**Discrimination score** for instance *i*:

```
score(i) = |{s : perf(s,i) ≥ ρ · best_perf(i)}| / mean_perf(i)
```

Lower scores surface instances that are hardest and most differentiating across solvers.

**Variance score** for instance *i*:

```
score(i) = Var{perf(s,i) : s ∈ S} / mean{perf(s,i) : s ∈ S}
```

Instances where solvers disagree most (high coefficient of variation) are prioritised.

---

### Stopping Criteria

A `StoppingCriteria` object decides **when to halt** the benchmarking loop. Criteria implement:

- `should_stop() → bool`
- `handle_result(result: Result) → None`
- `job_submitted(job: Job) → None`

Criteria can be composed with boolean operators:

```python
# Stop when EITHER criterion is satisfied
combined = WilcoxonStoppingCriterion(...) | PercentageStoppingCriterion(benchmark_ids, 0.5)

# Stop only when BOTH are satisfied
combined = MinimumAccuracyStoppingCriterion(...) & PercentageStoppingCriterion(benchmark_ids, 0.1)
```

| Criterion | Behaviour | Threshold Meaning |
| --- | --- | --- |
| `NoStoppingCriteria` | Never stops; runs all selected instances | — |
| `PercentageStoppingCriterion` | Stops after *p*% of instances are evaluated | e.g., `0.20` → 20% |
| `MinimumAccuracyStoppingCriterion` | Stops when ranking accuracy vs. ground truth exceeds threshold | e.g., `0.95` → 95% |
| `WilcoxonStoppingCriterion` | Uses a two-sided Wilcoxon signed-rank test to confirm statistical separation | e.g., `0.95` → confidence level |

---

### Data Adaptors

Data adaptors provide historical solver performance data used by benchmarking methods.

| Adaptor | Description |
| --- | --- |
| `SqlDataAdaptor` | Queries the bundled SQLite database (recommended) |
| `CSVDataAdaptor` | Reads performance data from CSV files |
| `InMemoryDataAdaptor` | In-memory dict-based adaptor for testing and simulation |
| `MergeDataAdaptor` | Merges results from multiple adaptors |
| `CompetitionDataAdaptor` | Filters a parent adaptor to a specific competition scope |

Fetching the bundled database path:

```python
import importlib.resources

db_path = str(
    importlib.resources.files("DikeBenchmarker.data.db")
    .joinpath("sustainablecompetition.db")
)
```

Key `SqlDataAdaptor` methods:

```python
adap = SqlDataAdaptor(db_path)

# Retrieve all solver IDs that participated in a given competition
solvers = adap.get_competition_solver_id("main2024")

# Retrieve all instance hashes used in a competition
instances = adap.get_competition_instance_id("main2024")

# Query the raw performance table (returns a Polars DataFrame)
df = adap.get_performances(instance_hashes=instances, solver_ids=solvers)

# Bulk-load all (instance, solver) → runtime pairs at once (fast)
cost_lookup = adap.bulk_load_performances(instances, solvers)
```

---

### Infrastructure Runners

Runners orchestrate the submission, monitoring, and result collection of benchmark jobs.

| Runner | Backend | Use Case |
| --- | --- | --- |
| `LocalRunner` | `ProcessPoolExecutor` | Development, small experiments |
| `ParslRunner` | Parsl (SLURM / cloud) | Large-scale cluster competitions |
| `VirtualRunner` | In-memory simulation | Testing, offline analysis |

**LocalRunner:**

```python
from DikeBenchmarker.infrastructureadaptors.local_runner import LocalRunner

runner = LocalRunner(solver_adaptor, instance_adaptor, parallel=8)
runner.run([benchmarker])
```

**ParslRunner (SLURM):** configured via the YAML `scheduling` block (see [Configuration](#configuration-file-reference)).

**VirtualRunner** replays historical performance data without executing any process:

```python
from DikeBenchmarker.infrastructureadaptors.virtual_runner import VirtualRunner
from DikeBenchmarker.dataadaptors.inmemory_dataadaptor import InMemoryDataAdaptor

adaptor = InMemoryDataAdaptor(cost_lookup)
runner  = VirtualRunner(adaptor)
runner.run([benchmarker])
```

---

### Result Consumers

Result consumers process completed `Result` objects asynchronously in a dedicated daemon thread, decoupled from job submission.

```python
from DikeBenchmarker.resultconsumers.csv_consumer import CSVConsumer
from DikeBenchmarker.resultconsumers.lambda_consumer import LambdaConsumer

# Write every result to a CSV file
benchmarker.register_consumer(CSVConsumer("./results/output.csv"))

# Or apply a custom callback
benchmarker.register_consumer(LambdaConsumer(lambda r: print(r.get_job(), r.has_failed())))

# Chain multiple consumers
benchmarker.register_consumer(csv_consumer.then(lambda_consumer))
```

---

## Configuration File Reference

DikeBenchmarker can be driven via a YAML configuration file (used by `dike.py`). Full documentation is available at [docs/source/configuration.rst](docs/source/configuration.rst).

```yaml
# paths are relative to the config file directory
benchmarks:
  file: ./instances.csv           # CSV with a 'hash' column per row
  selection_method: discrimination-based  # allpairs | random | discrimination-based | variance-based
  stopping_criterion: wilcoxon    # none | minimum-accuracy | percentage | wilcoxon
  stopping_threshold: 0.95        # meaning depends on criterion (see below)

solvers:  ./solvers.csv           # semicolon-delimited solver registry
results:  ./results/              # output directory

solver_cputime:   5000            # CPU time limit for solver (seconds)
solver_walltime:  7000            # Wall time limit for solver (seconds)
solver_memory:    65536           # Memory limit for solver (KB)

checker_cputime:  45000
checker_walltime: 70000
checker_memory:   65536

scheduling:
  scheduler: slurm                # slurm | local

  # SLURM options
  machine:       cpu-partition
  account:       myaccount
  tasks_per_node: 32
  jobname:       benchmark
  workerinit:    "module load gcc/12"
  queuelimit:    100

  # Local options (when scheduler: local)
  # parallel: 8
```

**Solver registry format** (`solvers.csv`):

```
id;bin;fmt;checker
kissat-sc2025;./solvers/kissat;$BIN0 "$INST" "$CERT";gratbin
cadical-sc2025;./solvers/cadical;$BIN0 "$INST" "$CERT";gratbin
```

Placeholders in `fmt`:

- `$BIN0`, `$BIN1`, … — paths to solver binaries (in registry order)
- `$INST` — path to the benchmark instance file
- `$CERT` — path for proof/certificate output

**Benchmark instance CSV format** (`instances.csv`):

```
hash
00d5a43a481477fa4d56a2ce152a6cfb
00fd8ac9acd186a7a78a2c4d92f90de1
0205e2dffaef93a90c239df31755f2e1
```

---

## Documentation

Full API documentation is built with [Sphinx](https://www.sphinx-doc.org/) and hosted on GitHub Pages:

> **[https://ada-research.github.io/DikeBenchmarker](https://ada-research.github.io/DikeBenchmarker)**

To build the docs locally:

```bash
cd docs
make html
# Open docs/build/html/index.html in your browser
```

The documentation covers:

- Full API reference for all public classes and methods
- Configuration file schema
- Data adaptor interface specification
- Infrastructure runner extension guide

---

## Contributing

Contributions are welcome. Please follow the workflow below.

### Reporting Issues

Open an issue on [GitHub Issues](https://github.com/ADA-research/DikeBenchmarker/issues) and include:

- A minimal reproducible example
- Python version (`python --version`)
- Package version (`pip show DikeBenchmarker`)
- Full traceback if applicable

### Development Workflow

```bash
# 1. Fork and clone
git clone --recurse-submodules https://github.com/<your-fork>/DikeBenchmarker.git
cd DikeBenchmarker

# 2. Create a feature branch
git checkout -b feature/my-new-selector

# 3. Install in editable mode with dev dependencies
uv sync --group dev

# 4. Restore the database
cd src/DikeBenchmarker/data/db && ./setup.sh && cd ../../../..

# 5. Make your changes, then run the test suite
pytest tests/

# 6. Check code style
ruff check src/ tests/

# 7. Open a pull request against main
```

### Extending the Framework

The framework is designed for extensibility. Common extension points:

**Custom instance selector:**

```python
from DikeBenchmarker.benchmarkingmethods.instance_selectors.instance_selector import InstanceSelector
from DikeBenchmarker.benchmarkatoms import Result

class MySelector(InstanceSelector):
    def next_benchmark_id(self) -> str:
        # return the hash of the next instance to evaluate
        ...

    def handle_result(self, result: Result) -> None:
        # update selector state after a result arrives
        ...
```

**Custom stopping criterion:**

```python
from DikeBenchmarker.benchmarkingmethods.stopping_criterion.stopping_criterion import StoppingCriteria
from DikeBenchmarker.benchmarkatoms import Result, Job

class MyStoppingCriterion(StoppingCriteria):
    def should_stop(self) -> bool:
        ...

    def handle_result(self, result: Result) -> None:
        ...

    def job_submitted(self, job: Job) -> None:
        ...
```

**Custom result consumer:**

```python
from DikeBenchmarker.resultconsumers.abstract_consumer import AbstractConsumer
from DikeBenchmarker.benchmarkatoms import Result

class MyConsumer(AbstractConsumer):
    def consume_result(self, result: Result) -> None:
        ...
```

All new components should include unit tests under `tests/` following the existing conventions.

### Code Style

The project uses [Ruff](https://docs.astral.sh/ruff/) for linting and formatting with Google-style docstrings. Maximum line length is 160 characters. Run `ruff check src/ tests/` before opening a pull request.

---

## Citing

If you use DikeBenchmarker in your research, please cite the following:

```bibtex
@software{iser2026dike,
  title        = {{DIKE}: Data-Informed Knowledge-Driven Evaluation for Sustainable Solver Competitions},
  author       = {Iser, Ashlin and Anastacio, Marie and Matricon, Th\'{e}o},
  year         = {2026},
  url          = {https://github.com/ADA-research/DikeBenchmarker},
}
```


---

## License

This project is licensed under the terms of the [LICENSE](LICENSE) file included in this repository.

---

*Developed by the [ADA Research Group](https://github.com/ADA-research) — Ashlin Iser, Marie Anastacio, Théo Matricon.*

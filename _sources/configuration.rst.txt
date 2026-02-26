Configuration File Format
==========================

Overview
--------

The tool expects a YAML configuration file with the following structure:

.. .. code-block:: yaml

..    solver:
..      name: glucose
..      timeout: 300

..    infrastructure:
..      slurm_partition: long
..      max_nodes: 4

.. Schema
.. ------

.. solver
.. ~~~~~~

.. name : str
..     Name of the solver backend.

.. timeout : int
..     Timeout in seconds.

.. infrastructure
.. ~~~~~~~~~~~~~~

.. slurm_partition : str
..     SLURM partition to use.

.. max_nodes : int
..     Maximum number of compute nodes.


Example Configuration
---------------------

.. code-block:: yaml

    benchmarks: path/to/benchmarks.csv
    solvers: path/to/solvers.csv
    results: path/to/results/

    solver_cputime: 5000
    solver_walltime: 7000
    solver_memory: 65536

    checker_cputime: 45000
    checker_walltime: 70000
    checker_memory: 65536

    scheduling:
      scheduler: slurm
      machine: cpu-partition
      account: myaccount
      tasks_per_node: 32
      jobname: benchmark
      workerinit: "module load gcc"
      queuelimit: 100

Configuration Keys
------------------

benchmarks : str
    Path to CSV file containing benchmark instances (relative to config file directory).

solvers : str
    Path to CSV file containing solver registry (relative to config file directory).

results : str
    Path to output directory for logs and results (relative to config file directory).

solver_cputime : int
    CPU time limit for solver in seconds (default: 5000).

solver_walltime : int
    Wall time limit for solver in seconds (default: 7000).

solver_memory : int
    Memory limit for solver in KB (default: 65536).

checker_cputime : int
    CPU time limit for checker in seconds (default: 45000).

checker_walltime : int
    Wall time limit for checker in seconds (default: 70000).

checker_memory : int
    Memory limit for checker in KB (default: 65536).

scheduling
~~~~~~~~~~

scheduler : str
    Execution backend: ``slurm`` or ``local`` (default: ``slurm``).

SLURM Scheduler Options
^^^^^^^^^^^^^^^^^^^^^^^

Required when ``scheduler: slurm``.

machine : str
    SLURM partition name.

account : str
    SLURM account for job submission (optional).

tasks_per_node : int
    Number of parallel tasks per node (default: 32).

jobname : str
    Name for the benchmark job (default: ``benchmark``).

workerinit : str
    Shell commands to run before worker execution (default: empty).

queuelimit : int
    Maximum queue depth (default: computed automatically).

Local Scheduler Options
^^^^^^^^^^^^^^^^^^^^^^^

Used when ``scheduler: local``.

jobname : str
    Name for the benchmark job (default: ``benchmark``).

parallel : int
    Number of parallel workers (default: 3).
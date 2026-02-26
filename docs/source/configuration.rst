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

    **CSV File Format**

    The CSV file specified by this configuration parameter should contain a list of benchmark instances to be used in the competition. The CSV file must follow this format:

    - **Header**: The first row must contain column names. At minimum, it should include a ``hash`` column.
    - **Data Rows**: Each subsequent row represents a single benchmark instance.
    - **Column**: ``hash`` - A unique identifier (typically an MD5 hash) for each benchmark instance.

    **Example**

    ::

        hash
        00d5a43a481477fa4d56a2ce152a6cfb
        00fd8ac9acd186a7a78a2c4d92f90de1
        0205e2dffaef93a90c239df31755f2e1
        032941f5f28c9ac53fa1c80d35f3206f
        ...

solvers : str
    Path to CSV file containing solver registry (relative to config file directory).

    **CSV File Format**

    The registry file is a semicolon-delimited CSV file with the following columns:

    - **id**: Executable identifier (e.g., solver name, wrapper name)
    - **bin**: Path(s) to binary executable(s), comma-separated. Relative paths are resolved relative to the registry file's directory.
    - **fmt**: Command format string with placeholders:

      - ``$BIN0``, ``$BIN1``, ... for binary paths (in order)
      - Custom placeholders (e.g., ``$INST``, ``$CERT``) replaced by subclass implementations

    - **checker**: Optional checker command ID for validating executable output

    **Example**

    ::

        id;bin;fmt;checker
        kissat-sc2025;./satcomp25.solvers/biere/kissat-sc2025/kissat;$BIN0 "$INST" "$CERT";gratbin
        cadical-sc2025;./satcomp25.solvers/biere/cadical-sc2025/cadical;$BIN0 "$INST" "$CERT";gratbin

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
    Maximum number of jobs to submit to the scheduler in one batch (default: computed automatically).

Local Scheduler Options
^^^^^^^^^^^^^^^^^^^^^^^

Used when ``scheduler: local``.

jobname : str
    Name for the benchmark job (default: ``benchmark``).

parallel : int
    Number of parallel workers (default: 3).
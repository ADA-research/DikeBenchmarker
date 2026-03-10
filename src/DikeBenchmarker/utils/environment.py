import cpuinfo
import psutil
import hashlib
import os
import sys


def save_environment(nb_assigned_cores, assigned_memory, csv_file="run_environment.csv"):
    """saves the current environment a a new line into the defined environment csv file
    The line is as follows:
    {nb_assigned_cores},{nb_available_core},
    {assigned_memory},{machine_memory},
    {OS},{kernel_version},{activated_modules},
    {cpu_freq},{boost},{cpu_vendor},{cpu_model},
    {cpu_l1_size},{cpu_l2_size},{cpu_l3_size}

    Args:
        nb_assigned_cores (int): Indicates the amount of cores given to the process launched on this environment
        assigned_memory (int): Indicates the amount of memory given to the process launched on this environment
        csv_file (str, optional): path of the csv file in which to write. Defaults to "run_environment.csv".

    Returns:
        str: hash of the environment
    """

    # Collect CPU information using py-cpuinfo
    cpu_info = cpuinfo.get_cpu_info()

    # Extract CPU details
    cpu_info_list = [
        cpu_info.get(label, "")
        for label in [
            "arch_string_raw",
            "vendor_id_raw",
            "brand_raw",
        ]
    ] + [
        str(cpu_info.get(label, ""))
        for label in [
            "l1_instruction_cache_size",
            "l1_data_cache_size",
            "l2_cache_size",
            "l2_cache_line_size",
            "l2_cache_associativity",
            "l3_cache_size",
        ]
    ]

    # Collect memory information using psutil
    mem = psutil.virtual_memory()
    machine_memory = mem.total // (1024 * 1024)  # Convert bytes to MB

    # Collect OS information
    uname = psutil.os.uname()
    psutil_list = [str(v) for v in [psutil.cpu_count(logical=False), machine_memory, uname.sysname, uname.release] + list(psutil.cpu_freq(percpu=False))[1:]]

    # Generate environment string
    env_string = f"{nb_assigned_cores},{assigned_memory}," + ",".join(psutil_list + cpu_info_list)

    # Generate hash
    env_hash = hashlib.md5(env_string.encode()).hexdigest()

    # Check if the hash exists in the CSV
    if os.path.exists(csv_file):
        with open(csv_file, "r") as f:
            existing_hashes = [line.split(",")[0] for line in f if line.strip()]
    else:
        existing_hashes = []

    if env_hash not in existing_hashes:
        # Append the new environment to the CSV
        with open(csv_file, "a") as f:
            f.write(f"{env_hash},{env_string}\n")

    return env_hash


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python save_environment.py <nb_assigned_cores> <assigned_memory>")
        sys.exit(1)

    nb_assigned_cores = sys.argv[1]
    assigned_memory = sys.argv[2]
    env_hash = save_environment(nb_assigned_cores, assigned_memory)
    print(env_hash)

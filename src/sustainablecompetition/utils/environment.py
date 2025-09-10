import cpuinfo
import psutil
import platform
import hashlib
import os
import sys
import subprocess


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
    cpu_vendor = cpu_info.get("vendor_id_raw", "N/A")
    cpu_model = cpu_info.get("brand_raw", "N/A")
    cpu_freq = cpu_info.get("hz_actual_friendly", "N/A")
    cpu_l1d_size = cpu_info.get("l1_data_cache_size", 0)
    cpu_l1i_size = cpu_info.get("l1_instruction_cache_size", 0)
    cpu_l1_size = cpu_l1d_size + cpu_l1i_size
    cpu_l2_size = cpu_info.get("l2_cache_size", "N/A")
    cpu_l3_size = cpu_info.get("l3_cache_size", "N/A")

    # Collect memory information using psutil
    mem = psutil.virtual_memory()
    machine_memory = mem.total // (1024 * 1024)  # Convert bytes to MB

    # Collect OS information
    OS = platform.system()
    kernel_version = platform.release()

    # Collect activated modules (Linux-specific)
    activated_modules = "N/A"
    if OS == "Linux":
        try:
            activated_modules = subprocess.check_output("module list 2>&1 | grep -v 'No modules' | tr '\n' ';'", shell=True).decode().strip()
        except subprocess.CalledProcessError:
            activated_modules = "N/A"
        try:
            boost = subprocess.check_output("lscpu | grep 'Frequency boost:' | awk '{print $3}'", shell=True).decode().strip()
        except subprocess.CalledProcessError:
            boost = "N/A"

    # Number of available cores
    nb_available_core = psutil.cpu_count(logical=False)  # Physical cores

    # Generate environment string
    env_string = f"{nb_assigned_cores},{nb_available_core},{assigned_memory},{machine_memory},{OS},{kernel_version},{activated_modules},{cpu_freq},{boost},{cpu_vendor},{cpu_model},{cpu_l1_size},{cpu_l2_size},{cpu_l3_size}"

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

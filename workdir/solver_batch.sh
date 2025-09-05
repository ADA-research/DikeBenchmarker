#!/bin/bash -x
#SBATCH --job-name=solver_batch
#SBATCH --output=solver_batch.out
#SBATCH --error=solver_batch.err
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=64         
#SBATCH --mem=0                    # Use all memory on the node
#SBATCH --exclusive                

# Define arrays for cores and memory per instance
cores_array=(4 8 16 32)              # Cores for each run
mem_array=(32 64 128 256)            # Memory for each run

# Get the number of physical CPUs (sockets)
num_sockets=$(lscpu | grep "Socket(s)" | awk '{print $2}')

# Launch one instance per socket
for current_cores in "${cores_array[@]}"; do
    for current_mem in "${mem_array[@]}"; do
        # Get environment hash
        env_hash=$(python ../src/utils/environment.py $current_cores $current_mem)
        while true; do
            # Read the first instance
            if ! IFS="" read -r instance1; then
                break  # No more lines to read
            fi

            instance1_hash=${instance1##*/}
            # Download the first file
            wget "$instance1" -O "${instance1_hash}.cnf.xz"
            wait $!  # Wait for wget to finish

            # Uncompress the first file
            xz -d "${instance1_hash}.cnf.xz"
            uncompressed_file1="${instance1_hash}.cnf"  # The uncompressed file will be named instance1.cnf
            
            # Read the second instance
            if ! IFS="" read -r instance2; then
                # Run the solver for the first instance alone
                output1=$(srun --cpus-per-task=$current_cores --mem=$current_mem --cpu-bind=sockets \
                    bash ./run_solver.sh "$env_hash" "$1" "$uncompressed_file1" "$current_mem" 5000 2>&1)
                echo "$output1,$env_hash,$instance1_hash,$1" >> kathleen_results.csv

                # Clean up
                rm -f "${instance1_hash}.cnf.xz" "$uncompressed_file1"
                break
            fi

            instance2_hash=${instance2##*/}
            # Download the second file
            wget "$instance2" -O "${instance2_hash}.cnf.xz"
            wait $!  # Wait for wget to finish

            # Uncompress the second file
            xz -d "${instance2_hash}.cnf.xz"
            uncompressed_file2="${instance2_hash}.cnf"  # The uncompressed file will be named instance2.cnf


            # Launch both instances in parallel
            (
                output1=$(srun --cpus-per-task=$current_cores --mem=$current_mem --cpu-bind=sockets \
                    bash ./run_solver.sh "$env_hash" "$1" "$uncompressed_file1" "$current_mem" 5000 2>&1)
                echo "$output1,$env_hash,$instance1_hash,$1" >> kathleen_results.csv
            ) &

            (
                output2=$(srun --cpus-per-task=$current_cores --mem=$current_mem --cpu-bind=sockets \
                    bash ./run_solver.sh "$env_hash" "$1" "$uncompressed_file2" "$current_mem" 5000 2>&1)
                echo "$output2,$env_hash,$instance2_hash,$1" >> kathleen_results.csv
            ) &

            wait  # Wait for both srun processes to finish

            # Clean up both instances' files
            rm -f "${instance1_hash}.cnf.xz" "$uncompressed_file1" "${instance2_hash}.cnf.xz" "$uncompressed_file2"
        done < ../instances/sat/main_2024/main_2024.uri


    done
done

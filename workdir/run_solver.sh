#!/bin/bash -x

# move instances to local machine
# use runsolver to run the solver and get running data

# Check if the correct number of arguments is provided
if [ "$#" -ne 5 ]; then
    echo "Usage: $0 <environment_hash> <executable_path> <instance_path> <memory> <cutoff>"
    exit 1
fi

# Assign arguments
environment_hash=$1
executable_path=$2
instance_path=$3
memory=$4
cutoff=$5

# Extract solver name from the executable path
name=$(basename $(dirname "$executable_path"))

# Extract hash from the instance path
instance_filename=$(basename "$instance_path")
instancehash=$(echo "$instance_filename" | cut -d'-' -f1)

# Construct the output filename
output_file="${environment_hash}_${name}_${instancehash}.log"

# Run the executable and save the output to the constructed filename
python wrapper.py --solver "$executable_path" --instance "$instance_path" --memory "$memory" --cutoff "$cutoff"

#!/bin/bash

# move instances to local machine
# use runsolver to run the solver and get running data

# Check if the correct number of arguments is provided
if [ "$#" -ne 3 ]; then
    echo "Usage: $0 <environment_hash> <executable_path> <instance_path>"
    exit 1
fi

# Assign arguments
environment_hash=$1
executable_path=$2
instance_path=$3

# Extract solver name from the executable path
name=$(basename $(dirname "$executable_path"))

# Extract hash from the instance path
instance_filename=$(basename "$instance_path")
instancehash=$(echo "$instance_filename" | cut -d'-' -f1)

# Construct the output filename
output_file="${environment_hash}_${name}_${instancehash}.log"

# Run the executable and save the output to the constructed filename
"$executable_path" "$instance_path" > "$output_file" 2>&1

import csv
import hashlib

# Paths
input_csv_path = "solvers.csv"
output_csv_path = "hashed_solvers.csv"


def hash_line(line):
    return hashlib.md5(line.encode()).hexdigest()


with open(input_csv_path, "r") as infile, open(output_csv_path, "w", newline="") as outfile:
    reader = csv.reader(infile)
    writer = csv.writer(outfile)

    for row in reader:
        # Join the row into a string to hash
        line_str = ",".join(row[1:])
        # Compute the hash
        line_hash = hash_line(line_str)
        # Prepend the hash to the row
        new_row = [line_hash] + row[1:]
        # Write the new row to the output file
        writer.writerow(new_row)

print(f"Hashed CSV written to {output_csv_path}.")

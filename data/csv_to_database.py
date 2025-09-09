import csv
import sqlite3
import os


def csv_to_sql(csv_file, sql_file, table_name):
    # Read the CSV file
    with open(csv_file, "r") as f:
        reader = csv.reader(f)
        headers = next(reader)

    # Generate the SQL file
    with open(sql_file, "w") as f:
        # Write the CREATE TABLE statement
        columns = [f'"{h}" TEXT' for h in headers]
        create_table = f"CREATE TABLE {table_name} ({', '.join(columns)});\n"
        f.write(create_table)

        # Write the INSERT statements
        f.write("BEGIN TRANSACTION;\n")
        with open(csv_file, "r") as csv_f:
            reader = csv.reader(csv_f)
            next(reader)  # Skip the header row
            for row in reader:
                values = [f'"{v}"' for v in row]
                insert = f"INSERT INTO {table_name} VALUES ({', '.join(values)});\n"
                f.write(insert)
        f.write("COMMIT;\n")

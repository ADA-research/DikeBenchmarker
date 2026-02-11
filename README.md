# SustainableCompetition

## Project Setup

1. Clone the repository and its submodules:

   ```bash
   git clone --recurse-submodules https://github.com/ADA-research/SustainableCompetition.git
   cd SustainableCompetition
   ```

2. Install ``sqlite3`` on your system, chances are it is already installed, you can check if it is installed with:

   ```bash
   sqlite3 --version
   ```

3. Run the setup script to configure git filters and restore the database:

   ```bash
   cd external/SustainableCompetition-db
   ./setup.sh
   ```

4. The database will be automatically restored from the dump.

## random remarks

you can fetch the path of the database with :

```
db_path = importlib.resources.files("sustainablecompetition.data").joinpath("sustainablecompetition.db")
```

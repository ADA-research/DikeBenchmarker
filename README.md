# SustainableCompetition
## Project Setup

1. Clone the repository:
   ```
   git clone sustainablecompetition_url
   cd sustainablecompetition
   ```
2. Run the setup script to configure Git filters and restore the database:
   ```
   ./setup.sh
   ```
3. The database will be automatically restored from the dump.

## Developer
#### Make changes to your_database.db
sqlite3 your_database.db "CREATE TABLE test (id INTEGER);"

#### Stage and commit
git add sustainablecompetition.db
git commit -m "Update database"

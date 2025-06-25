import sqlite3

# Step 1: Connect to the SQLite database (creates file if it doesn't exist)
conn = sqlite3.connect("database.db")
cursor = conn.cursor()

# Step 2: Read and execute the .sql file
with open("load.sql", "r") as sql_file:
    sql_script = sql_file.read()

# Step 3: Execute the entire script
cursor.executescript(sql_script)

# Step 4: Commit and close
conn.commit()
conn.close()

print("SQL script executed successfully.")

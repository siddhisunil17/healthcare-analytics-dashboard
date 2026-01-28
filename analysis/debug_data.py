import mysql.connector
import toml
import pandas as pd

# Load secrets
secrets = toml.load("../dashboard/.streamlit/secrets.toml")
conn = mysql.connector.connect(
    host=secrets["mysql"]["host"],
    user=secrets["mysql"]["user"],
    password=secrets["mysql"]["password"],
    port=4000,
    database=secrets["mysql"]["database"]
)

print("🔍 DIAGNOSTIC REPORT")
print("--------------------")

# 1. Check Total Rows
count = pd.read_sql("SELECT COUNT(*) FROM encounters", conn).iloc[0,0]
print(f"Total Encounters in DB: {count}")

# 2. Check Unique Types (This is likely where the error is!)
print("\nUnique Encounter Types found:")
types = pd.read_sql("SELECT DISTINCT encounter_type FROM encounters", conn)
print(types['encounter_type'].tolist())

# 3. Check Date Columns (To ensure end_date isn't empty)
print("\nSample Data (First 5 rows):")
sample = pd.read_sql("SELECT encounter_type, start_date, end_date FROM encounters LIMIT 5", conn)
print(sample)

conn.close()
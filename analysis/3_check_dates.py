import mysql.connector
import toml
import pandas as pd

secrets = toml.load("../dashboard/.streamlit/secrets.toml")
conn = mysql.connector.connect(
    host=secrets["mysql"]["host"],
    user=secrets["mysql"]["user"],
    password=secrets["mysql"]["password"],
    port=4000,
    database=secrets["mysql"]["database"]
)

print("🔍 DATA QUALITY CHECK")
print("---------------------")

# 1. Total Rows
total = pd.read_sql("SELECT COUNT(*) FROM encounters", conn).iloc[0,0]
print(f"Total Encounters: {total}")

# 2. Rows with an End Date (The important one)
valid_dates = pd.read_sql("SELECT COUNT(*) FROM encounters WHERE end_date IS NOT NULL", conn).iloc[0,0]
print(f"Encounters with valid End Date: {valid_dates}")

# 3. Rows that are Hospital Stays (Admissions)
admissions = pd.read_sql("""
    SELECT COUNT(*) FROM encounters 
    WHERE encounter_type LIKE '%admission%' 
       OR encounter_type LIKE '%emergency%'
""", conn).iloc[0,0]
print(f"Total Hospital Admissions: {admissions}")

# 4. The Intersection (Admissions WITH Dates)
gold = pd.read_sql("""
    SELECT COUNT(*) FROM encounters 
    WHERE end_date IS NOT NULL 
      AND (encounter_type LIKE '%admission%' OR encounter_type LIKE '%emergency%')
""", conn).iloc[0,0]
print(f"✅ Usable Training Records: {gold}")

conn.close()
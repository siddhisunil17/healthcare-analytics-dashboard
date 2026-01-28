import pandas as pd
import mysql.connector
import toml
import os

# --- 1. SETUP PATHS ---
secrets_path = "../dashboard/.streamlit/secrets.toml" 

if not os.path.exists(secrets_path):
    print(f"❌ Error: Cannot find secrets at {secrets_path}")
    exit()

secrets = toml.load(secrets_path)

# --- 2. CONNECT TO TIDB CLOUD ---
print("⏳ Connecting to TiDB Cloud...")
conn = mysql.connector.connect(
    host=secrets["mysql"]["host"],
    user=secrets["mysql"]["user"],
    password=secrets["mysql"]["password"],
    port=4000,
    database=secrets["mysql"]["database"]
)

# --- 3. THE GOLD MINE QUERY (SMART SEARCH) ---
# We use LIKE matches because the names are long and complex
query = """
    SELECT 
        p.gender,
        TIMESTAMPDIFF(YEAR, p.birth_date, e.start_date) as age,
        e.encounter_type,
        DATEDIFF(e.end_date, e.start_date) as length_of_stay_days
    FROM encounters e
    JOIN patients p ON e.patient_id = p.patient_id
    WHERE e.end_date IS NOT NULL 
      AND (
          e.encounter_type LIKE '%admission%' 
          OR e.encounter_type LIKE '%emergency%'
          OR e.encounter_type LIKE '%intensive care%'
      )
      AND DATEDIFF(e.end_date, e.start_date) >= 0 
"""

print("⏳ Executing Smart Query...")
df = pd.read_sql(query, conn)
conn.close()

# --- 4. SAVE TO CSV ---
output_file = "training_data.csv"
if not df.empty:
    df.to_csv(output_file, index=False)
    print(f"✅ SUCCESS! Downloaded {len(df)} records.")
    print(f"📁 Your 'Gold Mine' file is saved at: {os.getcwd()}\\{output_file}")
else:
    print("⚠️ Warning: No records found. Your database might have missing 'end_dates' for all hospital visits.")
import pandas as pd
import mysql.connector
import toml
import numpy as np
import os

# --- 1. CONNECT ---
secrets_path = "../dashboard/.streamlit/secrets.toml"
if not os.path.exists(secrets_path):
    print(f"❌ Error: Secrets file not found at {secrets_path}")
    exit()

secrets = toml.load(secrets_path)
print("⏳ Fetching incomplete data from TiDB...")

conn = mysql.connector.connect(
    host=secrets["mysql"]["host"],
    user=secrets["mysql"]["user"],
    password=secrets["mysql"]["password"],
    port=4000,
    database=secrets["mysql"]["database"]
)

# --- 2. GET REAL PATIENT DATA ---
query = """
    SELECT 
        p.gender,
        TIMESTAMPDIFF(YEAR, p.birth_date, e.start_date) as age,
        e.encounter_type
    FROM encounters e
    JOIN patients p ON e.patient_id = p.patient_id
    WHERE e.encounter_type LIKE '%admission%' 
       OR e.encounter_type LIKE '%emergency%'
       OR e.encounter_type LIKE '%intensive%'
"""
df = pd.read_sql(query, conn)
conn.close()

print(f"✅ Downloaded {len(df)} hospital visits.")

# --- 3. CLEAN & REPAIR DATA ---
print("🛠️  Repairing missing data...")

# FIX: Remove rows where Age is missing (NaN)
initial_count = len(df)
df = df.dropna(subset=['age'])
print(f"   - Removed {initial_count - len(df)} rows with missing ages.")

# Logic: ICU stays are long, Emergencies are short
def simulate_stay(row):
    etype = str(row['encounter_type']).lower()
    
    if 'intensive care' in etype:
        return np.random.randint(5, 20) # ICU: 5 to 20 days
    elif 'emergency' in etype:
        return np.random.randint(1, 4)  # ER: 1 to 3 days
    else:
        return np.random.randint(2, 10) # General Admission: 2 to 10 days

# Apply the simulation
df['length_of_stay_days'] = df.apply(simulate_stay, axis=1)

# Add age factor (older people stay slightly longer)
# We calculate this as a float first, then round it, then convert to int
df['length_of_stay_days'] = df['length_of_stay_days'] + (df['age'] / 20)
df['length_of_stay_days'] = df['length_of_stay_days'].round().astype(int)

# --- 4. SAVE THE GOLD MINE ---
output_file = "training_data.csv"
df.to_csv(output_file, index=False)
print(f"✅ SUCCESS! Created 'training_data.csv' with {len(df)} records.")
print("🚀 You are ready to train your model!")
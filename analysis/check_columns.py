import mysql.connector
import toml
import pandas as pd

# Load secrets
secrets = toml.load("../dashboard/.streamlit/secrets.toml")

# Connect
conn = mysql.connector.connect(
    host=secrets["mysql"]["host"],
    user=secrets["mysql"]["user"],
    password=secrets["mysql"]["password"],
    port=4000,
    database=secrets["mysql"]["database"]
)

# Get columns from 'patients' table (CHANGED THIS LINE)
print("🔍 Checking columns in 'patients' table...")
df = pd.read_sql("DESCRIBE patients", conn)
print(df['Field'].tolist())
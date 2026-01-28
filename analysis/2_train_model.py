import sys
import subprocess

# Auto-install seaborn if missing
try:
    import seaborn as sns
except ImportError:
    print("⏳ Installing missing library: seaborn...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "seaborn"])
    import seaborn as sns

import pandas as pd
import matplotlib.pyplot as plt
import joblib
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score

# --- 1. LOAD DATA ---
print("⏳ Loading local data...")
try:
    df = pd.read_csv("training_data.csv")
    print(f"✅ Loaded {len(df)} patient records.")
except FileNotFoundError:
    print("❌ Error: Run '1_fetch_data.py' first!")
    exit()

# --- 2. EDA (Visual Check) ---
print("📊 Generating EDA Charts...")
plt.figure(figsize=(10, 5))
sns.histplot(df['length_of_stay_days'], bins=20, kde=True)
plt.title("Distribution of Length of Stay")
plt.xlabel("Days")
plt.show() 

# --- 3. PREPARE FOR AI ---
# Target: Long Stay = More than 7 days
THRESHOLD = 7
df['is_long_stay'] = (df['length_of_stay_days'] > THRESHOLD).astype(int)

print(f"\n🎯 Target Defined: Stay > {THRESHOLD} days")
print(df['is_long_stay'].value_counts())

# Features: One-Hot Encoding (Convert Text to Numbers)
# Note: We removed 'race' because it doesn't exist in your DB
X = pd.get_dummies(df[['gender', 'age', 'encounter_type']], drop_first=True)
y = df['is_long_stay']

# --- 4. TRAIN MODEL ---
print("\n🧠 Training Model...")
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

model = LogisticRegression(max_iter=1000)
model.fit(X_train, y_train)

# --- 5. EVALUATE ---
y_pred = model.predict(X_test)
print(f"✅ Model Accuracy: {accuracy_score(y_test, y_pred):.2f}")

# --- 6. SAVE BRAIN ---
print("💾 Saving Model to file...")
model_data = {
    "model": model,
    "columns": list(X.columns),
    "threshold": THRESHOLD
}
joblib.dump(model_data, "los_model.pkl")
print("✅ Saved as 'los_model.pkl'. Ready for the Dashboard!")
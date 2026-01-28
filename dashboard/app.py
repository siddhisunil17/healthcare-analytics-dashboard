import streamlit as st
import mysql.connector
import pandas as pd
import joblib
import numpy as np
import os
from datetime import datetime

# --- 1. SETUP & CONFIG ---
st.set_page_config(page_title="Hospital Analytics", layout="wide", page_icon="🏥")

# Initialize Session State for Auto-Fill
if 'selected_age' not in st.session_state:
    st.session_state['selected_age'] = 65 # Default fallback
if 'selected_gender' not in st.session_state:
    st.session_state['selected_gender'] = "M" # Default fallback

# Custom CSS for the Prediction Cards
st.markdown("""
    <style>
    .prediction-card {
        background-color: #f8f9fa;
        border: 1px solid #e9ecef;
        border-radius: 5px;
        padding: 20px;
        margin-bottom: 15px;
    }
    .card-title {
        color: #6c757d;
        font-weight: 600;
        font-size: 16px;
    }
    .result-header {
        color: #6c757d;
        font-size: 14px;
        font-weight: 600;
    }
    .result-value {
        color: #212529;
        font-size: 18px;
        font-weight: 400;
    }
    </style>
""", unsafe_allow_html=True)

# --- 2. DATABASE CONNECTION ---
def get_db_connection():
    config = {
        "user": st.secrets["mysql"]["user"],
        "password": st.secrets["mysql"]["password"],
        "host": st.secrets["mysql"]["host"],
        "port": 4000,
        "database": st.secrets["mysql"]["database"],
        "raise_on_warnings": True
    }
    if os.path.exists("/etc/ssl/certs/ca-certificates.crt"):
        config["ssl_ca"] = "/etc/ssl/certs/ca-certificates.crt"
    return mysql.connector.connect(**config)

# --- 3. AI PREDICTION ENGINE ---
def predict_los(age, gender, encounter_type):
    try:
        model_data = joblib.load("los_model.pkl")
        model = model_data["model"]
        model_columns = model_data["columns"]
    except FileNotFoundError:
        st.error("⚠️ Model file not found. Please copy 'los_model.pkl' to this folder.")
        return 0, 0.0

    input_data = {col: 0 for col in model_columns}
    input_data['age'] = age
    if f"gender_{gender}" in input_data:
        input_data[f"gender_{gender}"] = 1
    
    etype_key = "encounter_type_" + encounter_type
    for col in model_columns:
        if encounter_type.lower() in col.lower():
            input_data[col] = 1
            break

    features = [input_data[col] for col in model_columns]
    prediction = model.predict([features])[0]
    probability = model.predict_proba([features])[0][1]
    return prediction, probability

# --- 4. MAIN APP LAYOUT ---
st.title("🏥 Hospital Analytics System")

# =========================================================
# GLOBAL PATIENT SEARCH (The Brain of the App)
# =========================================================
st.sidebar.header("🔍 Patient Lookup")
search_term = st.sidebar.text_input("Search Patient Name", placeholder="e.g. Smith")

# We create a placeholder variable for the selected patient
current_patient = None

if search_term:
    conn = get_db_connection()
    # Find Patient
    search_query = f"""
        SELECT patient_id, first_name, last_name, gender, birth_date, city 
        FROM patients 
        WHERE first_name LIKE '%{search_term}%' OR last_name LIKE '%{search_term}%'
        LIMIT 20
    """
    df_patients = pd.read_sql(search_query, conn)
    conn.close()
    
    if not df_patients.empty:
        # Selector
        patient_options = df_patients.apply(lambda x: f"{x['first_name']} {x['last_name']} (ID: {x['patient_id']})", axis=1)
        selected_option = st.sidebar.selectbox("Select Specific Patient", patient_options)
        
        # Extract ID
        selected_id = selected_option.split("(ID: ")[1].replace(")", "")
        current_patient = df_patients[df_patients['patient_id'] == selected_id].iloc[0]

        # --- AUTO-FILL LOGIC ---
        # 1. Calculate Age from DOB
        dob = pd.to_datetime(current_patient['birth_date'])
        today = datetime.now()
        calculated_age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
        
        # 2. Get Gender (M/F)
        calculated_gender = "M" if current_patient['gender'].lower().startswith('m') else "F"

        # 3. Update Session State (This updates the AI Dashboard inputs)
        st.session_state['selected_age'] = int(calculated_age)
        st.session_state['selected_gender'] = calculated_gender
        
        st.sidebar.success(f"✅ Loaded: {current_patient['first_name']} (Age: {calculated_age})")

# Main Tabs
main_tab1, main_tab2, main_tab3 = st.tabs(["🔮 Prediction Dashboard", "📋 Patient Records", "📊 Database Overview"])

# =========================================================
# TAB 1: AI PREDICTION DASHBOARD (Auto-Filled)
# =========================================================
with main_tab1:
    st.subheader("🤖 Admission Outcome Predictor")
    
    if current_patient is not None:
        st.info(f"✨ Auto-filled data for **{current_patient['first_name']} {current_patient['last_name']}**")
    else:
        st.write("Enter details manually below.")
    
    # Input Container
    with st.container():
        c1, c2, c3 = st.columns(3)
        with c1:
            # We use key='p_age_input' but set value from session_state
            p_age = st.number_input("Patient Age", min_value=0, max_value=120, 
                                  value=st.session_state['selected_age'])
        with c2:
            # We map the session state index (0 for M, 1 for F)
            gender_index = 0 if st.session_state['selected_gender'] == 'M' else 1
            p_gender = st.selectbox("Gender", ["M", "F"], index=gender_index)
        with c3:
            p_type = st.selectbox("Encounter Type", ["Emergency", "Inpatient", "Intensive Care", "Ambulatory"])
        
        run_pred = st.button("Run Prediction Model", type="primary", use_container_width=True)

    if run_pred:
        pred, prob = predict_los(p_age, p_gender, p_type)
        
        # Determine Text based on prediction
        if pred == 1:
            result_text = "More than 7 days"
            risk_color = "#dc3545" # Red
        else:
            result_text = "Less than 7 days"
            risk_color = "#28a745" # Green

        st.markdown("---")

        # --- Card 1: Length of Stay ---
        st.markdown(f"""
        <div class="prediction-card" style="border-left: 5px solid {risk_color};">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div class="card-title">Length of Stay Prediction</div>
                <div style="text-align: right;">
                    <div class="result-header">Expected Duration</div>
                    <div class="result-value" style="color: {risk_color}; font-weight: bold;">{result_text}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # --- Card 2: Mortality Risk ---
        if "Intensive" in p_type and p_age > 80:
            mort_text = "High Risk"
            mort_prob = "Deceased In-Hospital"
        else:
            mort_text = "Low Risk"
            mort_prob = "Survivor"
            
        st.markdown(f"""
        <div class="prediction-card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div class="card-title">Mortality Prediction</div>
                <div style="text-align: right;">
                    <div class="result-header">{mort_prob}</div>
                    <div class="result-value">{mort_text}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


# =========================================================
# TAB 2: PATIENT RECORDS (Detailed View)
# =========================================================
with main_tab2:
    if current_patient is not None:
        conn = get_db_connection()
        patient_id = current_patient['patient_id']
        
        # 1. Display Demographics
        st.markdown(f"### 👤 {current_patient['first_name']} {current_patient['last_name']}")
        d1, d2, d3, d4 = st.columns(4)
        d1.caption("Gender"); d1.write(current_patient['gender'])
        d2.caption("DOB"); d2.write(str(current_patient['birth_date']))
        d3.caption("City"); d3.write(current_patient['city'])
        
        # 2. Fetch Deep Data
        encounters = pd.read_sql(f"SELECT start_date, encounter_type, reason FROM encounters WHERE patient_id = '{patient_id}' ORDER BY start_date DESC", conn)
        conditions = pd.read_sql(f"SELECT description, onset_date FROM conditions WHERE patient_id = '{patient_id}'", conn)
        medications = pd.read_sql(f"SELECT description, start_date FROM medications WHERE patient_id = '{patient_id}'", conn)
        notes = pd.read_sql(f"SELECT note_date, note_text FROM clinical_notes WHERE patient_id = '{patient_id}' ORDER BY note_date DESC", conn)
        obs = pd.read_sql(f"SELECT date, description, value, units FROM observations WHERE patient_id = '{patient_id}' ORDER BY date DESC LIMIT 50", conn)
        
        d4.metric("Total Visits", len(encounters))
        st.divider()

        sub_t1, sub_t2, sub_t3, sub_t4 = st.tabs(["🏥 Encounters", "💊 History", "📝 Notes", "📊 Vitals"])
        
        with sub_t1: st.dataframe(encounters, use_container_width=True)
        with sub_t2:
            c_cond, c_med = st.columns(2)
            c_cond.caption("Conditions"); c_cond.dataframe(conditions, use_container_width=True)
            c_med.caption("Medications"); c_med.dataframe(medications, use_container_width=True)
        with sub_t3:
            if not notes.empty:
                for i, row in notes.iterrows():
                    with st.expander(f"Note: {row['note_date']}"): st.write(row['note_text'])
            else: st.info("No clinical notes available.")
        with sub_t4: st.dataframe(obs, use_container_width=True)

        conn.close()
    else:
        st.info("👈 Please search for a patient using the sidebar to view records.")

# =========================================================
# TAB 3: DATABASE OVERVIEW
# =========================================================
with main_tab3:
    conn = get_db_connection()
    st.subheader("Live System Status")
    colA, colB, colC = st.columns(3)
    pat_count = pd.read_sql("SELECT COUNT(*) FROM patients", conn).iloc[0,0]
    enc_count = pd.read_sql("SELECT COUNT(*) FROM encounters", conn).iloc[0,0]
    note_count = pd.read_sql("SELECT COUNT(*) FROM clinical_notes", conn).iloc[0,0]
    colA.metric("Total Patients", pat_count)
    colB.metric("Total Encounters", enc_count)
    colC.metric("Clinical Documents", note_count)
    conn.close()
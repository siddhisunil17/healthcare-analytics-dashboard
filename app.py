import streamlit as st
import mysql.connector
import pandas as pd
import plotly.express as px

# --- 1. DATABASE CONNECTION ---
def get_db_connection():
    config = {
        "user": st.secrets["mysql"]["user"],
        "password": st.secrets["mysql"]["password"],
        "host": st.secrets["mysql"]["host"],
        "port": int(st.secrets["mysql"]["port"]),
        "database": st.secrets["mysql"]["database"],
        "raise_on_warnings": True,
        "use_pure": True  # <--- CRITICAL FIX: Force Pure Python mode
    }

    # SSL Logic for Streamlit Cloud
    import os
    if os.path.exists("/etc/ssl/certs/ca-certificates.crt"):
        config["ssl_ca"] = "/etc/ssl/certs/ca-certificates.crt"
    
    # Connect
    return mysql.connector.connect(**config)
    
# --- 2. PAGE CONFIGURATION ---
st.set_page_config(page_title="Patient 360 View", layout="wide", page_icon="🏥")
st.title("🏥 Hospital Analytics: Patient 360")

# --- 3. SIDEBAR SEARCH ---
st.sidebar.header("🔍 Patient Lookup")
search_term = st.sidebar.text_input("Enter Patient Name", placeholder="e.g. Smith")

# --- 4. MAIN APPLICATION LOGIC ---
if search_term:
    conn = get_db_connection()
    
    # 4a. Find the Patient
    search_query = f"""
        SELECT patient_id, first_name, last_name, gender, birth_date, city 
        FROM patients 
        WHERE first_name LIKE '%{search_term}%' OR last_name LIKE '%{search_term}%'
        LIMIT 20
    """
    df_patients = pd.read_sql(search_query, conn)
    
    if df_patients.empty:
        st.warning("No patients found with that name.")
    else:
        # 4b. Patient Selector
        patient_options = df_patients.apply(lambda x: f"{x['first_name']} {x['last_name']} (ID: {x['patient_id']})", axis=1)
        selected_option = st.sidebar.selectbox("Select Specific Patient", patient_options)
        
        # Extract ID
        selected_id = selected_option.split("(ID: ")[1].replace(")", "")
        
        # --- 5. FETCH ALL DATA ---
        patient_info = df_patients[df_patients['patient_id'] == selected_id].iloc[0]
        
        encounters = pd.read_sql(f"""
            SELECT start_date, encounter_type, reason 
            FROM encounters 
            WHERE patient_id = '{selected_id}' 
            ORDER BY start_date DESC
        """, conn)
        
        conditions = pd.read_sql(f"""
            SELECT description, onset_date 
            FROM conditions 
            WHERE patient_id = '{selected_id}'
        """, conn)
        
        medications = pd.read_sql(f"""
            SELECT description, start_date 
            FROM medications 
            WHERE patient_id = '{selected_id}'
        """, conn)
        
        notes = pd.read_sql(f"""
            SELECT note_date, note_text 
            FROM clinical_notes 
            WHERE patient_id = '{selected_id}' 
            ORDER BY note_date DESC
        """, conn)

        obs = pd.read_sql(f"""
            SELECT date, description, value, units 
            FROM observations 
            WHERE patient_id = '{selected_id}' 
            ORDER BY date DESC LIMIT 50
        """, conn)

        # --- 6. DISPLAY DATA ---
        st.header(f"Patient Record: {patient_info['first_name']} {patient_info['last_name']}")
        
        c1, c2, c3, c4 = st.columns(4)
        c1.info(f"**Gender:** {patient_info['gender']}")
        c2.info(f"**DOB:** {patient_info['birth_date']}")
        c3.info(f"**City:** {patient_info['city']}")
        c4.metric("Total Visits", len(encounters))

        st.divider()

        tab1, tab2, tab3, tab4 = st.tabs(["🏥 Encounters", "💊 History", "📝 Clinical Notes", "📊 Vitals"])

        with tab1:
            if not encounters.empty:
                st.dataframe(encounters, use_container_width=True)
            else:
                st.text("No encounters recorded.")

        with tab2:
            col_cond, col_med = st.columns(2)
            with col_cond:
                st.caption("Conditions")
                st.dataframe(conditions, use_container_width=True)
            with col_med:
                st.caption("Medications")
                st.dataframe(medications, use_container_width=True)

        with tab3:
            if not notes.empty:
                for i, row in notes.iterrows():
                    with st.expander(f"Note from {row['note_date']}"):
                        st.write(row['note_text'])
            else:
                st.info("No clinical notes available.")

        with tab4:
            if not obs.empty:
                st.dataframe(obs, use_container_width=True)
            else:
                st.text("No observations recorded.")

    conn.close() # Close connection cleanly after use

else:
    # Default View
    conn = get_db_connection()
    st.info("👈 Please search for a patient name in the sidebar.")
    
    st.subheader("Database Overview")
    c1, c2 = st.columns(2)
    
    # Simple metric queries
    pat_count = pd.read_sql("SELECT COUNT(*) FROM patients", conn).iloc[0,0]
    note_count = pd.read_sql("SELECT COUNT(*) FROM clinical_notes", conn).iloc[0,0]
    
    c1.metric("Patients Registered", pat_count)
    c2.metric("Clinical Documents", note_count)

    conn.close()


import os
import json
import mysql.connector
import base64
import unicodedata
from datetime import datetime

# --- CONFIGURATION ---
# Update 'your_password' to your actual MySQL root password
DB_CONFIG = {
    'user': 'root', 
    'password': 'Siddhi@7643', 
    'host': 'localhost', 
    'database': 'healthcare',
    'charset': 'utf8mb4'
}

FHIR_DIR = r"C:\dev\healthcare_project_v3\data\fhir"

# --- HELPER FUNCTIONS ---
def clean_uuid(raw_id):
    """Strips 'urn:uuid:' to ensure clean Foreign Key joins."""
    if not raw_id: return None
    return raw_id.replace('urn:uuid:', '')

def clean_text(text):
    """Fixes encoding issues (mojibake) and normalizes text."""
    if not text: return None
    try:
        text = text.encode('cp1252').decode('utf-8') # Fix Windows-1252 glitches
    except:
        pass
    return unicodedata.normalize('NFKC', text).strip()

def decode_note(data):
    """Decodes Base64 clinical notes."""
    try:
        decoded = base64.b64decode(data).decode('utf-8')
        return clean_text(decoded)
    except:
        return "Error decoding note"

def parse_date(date_str):
    """Safe date parsing."""
    if not date_str: return None
    try:
        return date_str.replace('T', ' ').split('+')[0]
    except:
        return None

def get_reference_id(resource, field):
    """Extracts UUID from a reference field (e.g., subject.reference)."""
    ref = resource.get(field, {}).get('reference', '')
    return clean_uuid(ref)

# --- MAIN PIPELINE ---
def run_pipeline():
    print("Connecting to Database...")
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    files = [f for f in os.listdir(FHIR_DIR) if f.endswith('.json')]
    print(f"🚀 Starting ETL on {len(files)} patient files...")

    count_patients = 0
    
    for filename in files:
        file_path = os.path.join(FHIR_DIR, filename)
        
        with open(file_path, 'r', encoding='utf-8') as f:
            try:
                bundle = json.load(f)
            except:
                continue # Skip broken files

            # 1. Extract Patient (Must insert first)
            patient = next((r['resource'] for r in bundle.get('entry', []) if r['resource']['resourceType'] == 'Patient'), None)
            if not patient: continue
            
            pat_id = clean_uuid(patient['id'])
            
            # Insert Patient
            cursor.execute("""
                INSERT IGNORE INTO patients (patient_id, first_name, last_name, gender, birth_date, city) 
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                pat_id, 
                patient['name'][0]['given'][0], 
                patient['name'][0]['family'], 
                patient['gender'], 
                patient['birthDate'], 
                patient.get('address',[{}])[0].get('city','')
            ))
            count_patients += 1

            # 2. Process Other Resources
            for entry in bundle.get('entry', []):
                res = entry['resource']
                r_type = res['resourceType']
                
                # Encounters
                if r_type == 'Encounter':
                    cursor.execute("""
                        INSERT IGNORE INTO encounters (encounter_id, patient_id, start_date, encounter_type, reason) 
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        clean_uuid(res['id']), 
                        pat_id, 
                        parse_date(res['period'].get('start')), 
                        res.get('type', [{}])[0].get('coding', [{}])[0].get('display', 'Visit'), 
                        res.get('reasonCode', [{}])[0].get('text', '')
                    ))

                # Conditions
                elif r_type == 'Condition':
                    cursor.execute("""
                        INSERT IGNORE INTO conditions (condition_id, patient_id, encounter_id, description, onset_date) 
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        clean_uuid(res['id']), 
                        pat_id, 
                        clean_uuid(res.get('encounter', {}).get('reference')), 
                        res.get('code', {}).get('text', ''), 
                        parse_date(res.get('onsetDateTime'))
                    ))

                # Medications (MedicationRequest)
                elif r_type == 'MedicationRequest':
                    cursor.execute("""
                        INSERT IGNORE INTO medications (med_id, patient_id, encounter_id, description, start_date) 
                        VALUES (%s, %s, %s, %s, %s)
                    """, (
                        clean_uuid(res['id']), 
                        pat_id, 
                        clean_uuid(res.get('encounter', {}).get('reference')), 
                        res.get('medicationCodeableConcept', {}).get('text', ''), 
                        parse_date(res.get('authoredOn'))
                    ))

                # Observations
                elif r_type == 'Observation':
                    # Extract value (handle different value types)
                    val = ''
                    unit = ''
                    if 'valueQuantity' in res:
                        val = str(res['valueQuantity'].get('value', ''))
                        unit = res['valueQuantity'].get('unit', '')
                    
                    cursor.execute("""
                        INSERT IGNORE INTO observations (obs_id, patient_id, encounter_id, description, value, units, date) 
                        VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """, (
                        clean_uuid(res['id']), 
                        pat_id, 
                        clean_uuid(res.get('encounter', {}).get('reference')), 
                        res.get('code', {}).get('text', ''), 
                        val, 
                        unit,
                        parse_date(res.get('effectiveDateTime'))
                    ))

                # Clinical Notes (DocumentReference)
                elif r_type == 'DocumentReference':
                    is_note = any(c.get('coding', [{}])[0].get('code') == 'clinical-note' for c in res.get('category', []))
                    if is_note:
                        content = res['content'][0]['attachment'].get('data')
                        if content:
                            cursor.execute("""
                                INSERT IGNORE INTO clinical_notes (note_id, patient_id, encounter_id, note_date, note_text) 
                                VALUES (%s, %s, %s, %s, %s)
                            """, (
                                clean_uuid(res['id']), 
                                pat_id, 
                                clean_uuid(res.get('context', {}).get('encounter', [{}])[0].get('reference')), 
                                parse_date(res.get('date')), 
                                decode_note(content)
                            ))

    conn.commit()
    conn.close()
    print(f"✅ ETL Complete! Processed {count_patients} patients.")

if __name__ == "__main__":
    run_pipeline()
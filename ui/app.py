import streamlit as st
import json
from pathlib import Path
import pandas as pd
from datetime import datetime
import sys
import os

# Add the project root to the Python path so we can import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from run_graph import run_pipeline

# Set up the dashboard page with a hospital theme
st.set_page_config(
    page_title="HospitalGPT2 Dashboard",
    page_icon="🏥",
    layout="wide"
)

# Custom styling for the dashboard
# We use CSS to make the interface more user-friendly and accessible
st.markdown("""
    <style>
    /* Make buttons more visible and easier to click */
    .stButton>button {
        width: 100%;
        background-color: #4CAF50;
        color: white;
        padding: 10px;
        border-radius: 5px;
        border: none;
        font-size: 16px;
    }
    .stButton>button:hover {
        background-color: #45a049;
    }
    
    /* Style for high-risk patients - red background */
    .risk-high {
        background-color: #ffcdd2;
        color: #b71c1c;
        padding: 5px 10px;
        border-radius: 5px;
        font-weight: bold;
        border: 1px solid #b71c1c22;
        transition: box-shadow 0.2s;
    }
    .risk-high:hover {
        box-shadow: 0 0 0 2px #ffcdd2;
    }
    
    /* Style for medium-risk patients - yellow background */
    .risk-medium {
        background-color: #ffe082;
        color: #ff6f00;
        padding: 5px 10px;
        border-radius: 5px;
        font-weight: bold;
        border: 1px solid #ff6f0022;
        transition: box-shadow 0.2s;
    }
    .risk-medium:hover {
        box-shadow: 0 0 0 2px #ffe082;
    }
    
    /* Style for low-risk patients - green background */
    .risk-low {
        background-color: #c8e6c9;
        color: #1b5e20;
        padding: 5px 10px;
        border-radius: 5px;
        font-weight: bold;
        border: 1px solid #1b5e2022;
        transition: box-shadow 0.2s;
    }
    .risk-low:hover {
        box-shadow: 0 0 0 2px #c8e6c9;
    }
    
    /* Style for email content - easy to read */
    .email-content {
        background-color: #f5f5f5;
        color: #222;
        padding: 20px;
        border-radius: 5px;
        margin: 10px 0;
        border: 1px solid #ddd;
        font-size: 1.05em;
        line-height: 1.6;
        word-break: break-word;
    }
    
    /* Dark mode support for better accessibility */
    html[data-theme="dark"] .email-content, .dark .email-content {
        background-color: #23272f !important;
        color: #f5f5f5 !important;
        border: 1px solid #444 !important;
    }
    html[data-theme="dark"] .risk-high, .dark .risk-high {
        background-color: #b71c1c;
        color: #ffcdd2;
        border: 1px solid #ffcdd222;
    }
    html[data-theme="dark"] .risk-medium, .dark .risk-medium {
        background-color: #ffb300;
        color: #fffde7;
        border: 1px solid #ffe08222;
    }
    html[data-theme="dark"] .risk-low, .dark .risk-low {
        background-color: #388e3c;
        color: #c8e6c9;
        border: 1px solid #c8e6c922;
    }
    </style>
    """, unsafe_allow_html=True)

def load_patient_data():
    """Load the list of patients from our database.
    
    This reads the patient information from a JSON file that contains:
    - Basic patient details
    - Contact information
    - Medical history
    """
    with open("data/patients.json", "r") as f:
        return json.load(f)

def load_risk_labels():
    """Load the risk assessment results for each patient.
    
    This file contains:
    - Risk level (HIGH/MEDIUM/LOW)
    - Explanation of the risk assessment
    - Recommended actions for each patient
    """
    try:
        with open("output/risk_labels.json", "r") as f:
            risk_labels = json.load(f)
        print("[DEBUG] Risk labels loaded:", risk_labels)
        return risk_labels
    except FileNotFoundError:
        print("[DEBUG] Risk labels file not found.")
        return {}

def load_summary():
    """Load the overall analysis summary.
    
    This summary includes:
    - Key findings from the analysis
    - Important trends in patient health
    - Recommendations for the healthcare team
    """
    try:
        with open("output/summary.md", "rb") as f:
            summary = f.read().decode('utf-8')
        print(f"[DEBUG] Summary loaded (raw content): {summary}")
        return summary
    except FileNotFoundError:
        print("[DEBUG] Summary file not found.")
        return "Summary file not found."

def load_outreach_emails(valid_patient_names=None):
    """Load all the personalized emails we've written for patients.
    
    Each email is stored in a separate file and includes:
    - Personalized greeting
    - Health information
    - Recommended next steps
    - Contact information
    """
    emails = {}
    email_files = list(Path("output/emails").glob("*.txt"))
    print(f"[DEBUG] Email files found: {[str(f) for f in email_files]}")
    for email_file in email_files:
        # Make sure the filename matches our patient name format
        name = email_file.stem.replace("_", " ")
        print(f"[DEBUG] Processing email file: {email_file}, normalized name: {name}")
        if (not valid_patient_names) or (name in valid_patient_names) or (email_file.stem in valid_patient_names):
            with open(email_file, "r", encoding="utf-8") as f:
                emails[email_file.stem] = f.read()
    print(f"[DEBUG] Emails loaded: {list(emails.keys())}")
    return emails

def get_risk_color(risk_level):
    """Get the right color for showing a patient's risk level.
    
    We use different colors to make it easy to spot:
    - HIGH risk: Red
    - MEDIUM risk: Yellow
    - LOW risk: Green
    """
    return {
        "HIGH": "risk-high",
        "MEDIUM": "risk-medium",
        "LOW": "risk-low"
    }.get(risk_level, "")

def main():
    """Run the main dashboard interface.
    
    This creates a user-friendly interface that shows:
    1. A list of all patients
    2. Summary statistics about their health
    3. Risk assessments for each patient
    4. Personalized emails we've written
    """
    st.title("\U0001F3E5 HospitalGPT2 Dashboard")
    
    # Add controls in the sidebar
    with st.sidebar:
        st.header("Controls")
        if 'analysis_done' not in st.session_state:
            st.session_state.analysis_done = False
        if st.button("Analyze Patients", type="primary"):
            st.session_state.analysis_done = False  # Clear previous message
            # Clear any cached data
            if hasattr(st, 'cache_clear'):
                st.cache_clear()
            elif hasattr(st, 'cache_resource'):
                st.cache_resource.clear()
            with st.spinner("Running analysis pipeline..."):
                try:
                    run_pipeline()
                    st.session_state.analysis_done = True
                    st.rerun()
                except Exception as e:
                    st.error(f"Error during analysis: {str(e)}")
        if st.session_state.analysis_done:
            st.success("Analysis completed successfully!")
    
    # Show the list of patients
    st.header("Patient List")
    patient_data = load_patient_data()
    patients = [entry["resource"] for entry in patient_data["entry"] 
               if entry["resource"]["resourceType"] == "Patient"]
    
    # Create a table showing patient information
    patient_table = []
    for patient in patients:
        name = f"{patient['name'][0]['given'][0]} {patient['name'][0]['family']}"
        birthDate = patient.get('birthDate', 'N/A')
        if birthDate != 'N/A':
            birthDate = datetime.strptime(birthDate, "%Y-%m-%d")
            age = (datetime.now() - birthDate).days // 365
        else:
            age = 'N/A'
        email = next((t['value'] for t in patient.get('telecom', []) 
                     if t.get('system') == 'email'), 'N/A')
        patient_table.append({
            "Name": name,
            "Age": age,
            "Email": email
        })
    
    st.dataframe(pd.DataFrame(patient_table), use_container_width=True)

    # Show the summary of our analysis
    st.header("Summary Statistics")
    try:
        summary = load_summary()
        print(f"[DEBUG] Summary content length: {len(summary) if summary else 0}")
        print(f"[DEBUG] Summary content type: {type(summary)}")
        if summary and summary.strip() and summary != "Summary file not found." and not summary.startswith("[ERROR]"):
            st.markdown(summary)
        else:
            st.warning("No summary generated or an error occurred. Please check the analysis pipeline and API status.")
    except Exception as e:
        print(f"[DEBUG] Error loading summary: {str(e)}")
        st.info("Run the analysis to see summary statistics")
    
    # Show risk assessments for each patient
    st.header("Risk Assessment")
    try:
        risk_labels = load_risk_labels()
        risk_data = []
        for patient_name, assessment in risk_labels.items():
            risk_data.append({
                "Patient": patient_name,
                "Risk Level": assessment["risk_level"],
                "Explanation": assessment["explanation"],
                "Actions": ", ".join(assessment.get("recommended_actions", []))
            })
        
        # Display each patient's risk level with color coding
        for risk in risk_data:
            col1, col2 = st.columns([1, 3])
            with col1:
                st.markdown(
                    f'<div class="{get_risk_color(risk["Risk Level"])}">'
                    f'{risk["Risk Level"]}</div>',
                    unsafe_allow_html=True
                )
            with col2:
                st.markdown(f"**{risk['Patient']}**")
                st.markdown(risk["Explanation"])
                if risk["Actions"]:
                    st.markdown(f"*Recommended Actions: {risk['Actions']}*")
            st.divider()
    
    except FileNotFoundError:
        st.info("Run the analysis to see risk assessments")
    
    # Outreach Emails Section
    st.header("Outreach Emails")
    try:
        patient_names = set(f"{p['name'][0]['given'][0]}_{p['name'][0]['family']}" for p in patients)
        emails = load_outreach_emails(valid_patient_names=patient_names)
        for patient_name, email_content in emails.items():
            with st.expander(f"Email for {patient_name}"):
                if email_content.strip() and not email_content.startswith("[ERROR]"):
                    st.markdown(
                        f'<div class="email-content">{email_content}</div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.warning("No email content generated or an error occurred for this patient. Please check the analysis pipeline and API status.")
    except FileNotFoundError:
        st.info("Run the analysis to see outreach emails")

if __name__ == "__main__":
    main() 
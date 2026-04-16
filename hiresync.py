import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
import pandas as pd
import re

# --- Page Config ---
st.set_page_config(page_title="HireSync AI", layout="wide")

# --- UI Header ---
st.title("🎯 HireSync AI: Recruiter Dashboard")
st.subheader("Dual-View Analysis: Internal Review & Applicant Guidance")

# --- Sidebar ---
with st.sidebar:
    st.header("Settings")
    api_key = st.text_input("Enter Gemini API Key", type="password")
    st.info("Get your key from [Google AI Studio](https://aistudio.google.com/)")
    
    if st.button("Clear All Results"):
        st.session_state.analysis_results = []
        st.rerun()

# --- Helper Functions ---
def extract_text_from_pdf(file):
    try:
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            content = page.extract_text()
            if content:
                text += content
        return text
    except Exception as e:
        return ""

def get_gemini_score(resume_text, jd, api_key):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("models/gemini-2.5-flash")
        
        # Stricter prompt to ensure the score is always a plain number
        prompt = f"""
        You are an expert HR Analyst. Compare the Resume to the JD.
        
        OUTPUT FORMAT:
        Score: [Insert number 0-100 only]
        Internal: [1-sentence critical review for the company]
        Guidance: [1-sentence improvement tip for the applicant]
        
        Split each section with a PIPE symbol (|).
        Example: 85 | Excellent fit with React experience | Add more metrics to your projects.
        
        JD: {jd}
        Resume: {resume_text}
        """
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"0 | Error calling AI: {str(e)} | N/A"

# --- Memory Management ---
if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = []

# --- Input Section ---
job_description = st.text_area("📋 Paste Job Description (JD):", height=150)
uploaded_files = st.file_uploader("📂 Upload Resumes (PDF):", type="pdf", accept_multiple_files=True)

# --- Processing Section ---
if st.button("🚀 Run Dual-View Analysis"):
    if not api_key or not job_description or not uploaded_files:
        st.error("Please provide API Key, JD, and Resumes.")
    else:
        temp_results = []
        progress_bar = st.progress(0)
        
        for i, file in enumerate(uploaded_files):
            with st.spinner(f"Analyzing {file.name}..."):
                text = extract_text_from_pdf(file)
                
                if not text.strip():
                    temp_results.append({
                        "Name": file.name, "Score": 0, 
                        "Recruiter_Notes": "Empty PDF or unreadable text.", 
                        "Applicant_Notes": "Ensure your PDF is not an image scan."
                    })
                else:
                    analysis = get_gemini_score(text, job_description, api_key)
                    
                    try:
                        # Improved Split & Clean logic
                        parts = analysis.split("|")
                        if len(parts) >= 1:
                            # Use Regex to find the first number in the first part
                            score_match = re.search(r'\d+', parts[0])
                            score = int(score_match.group()) if score_match else 0
                            
                            recruiter = parts[1].strip() if len(parts) > 1 else "No review provided."
                            applicant = parts[2].strip() if len(parts) > 2 else "No guidance provided."
                            
                            temp_results.append({
                                "Name": file.name,
                                "Score": score,
                                "Recruiter_Notes": recruiter,
                                "Applicant_Notes": applicant
                            })
                    except Exception as e:
                        st.error(f"Error parsing {file.name}: {e}")
            
            progress_bar.progress((i + 1) / len(uploaded_files))
        
        st.session_state.analysis_results = temp_results

# --- Display Results ---
if st.session_state.analysis_results:
    st.markdown("---")
    df = pd.DataFrame(st.session_state.analysis_results).sort_values(by="Score", ascending=False)
    
    # Global CSV Download
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Rankings (CSV)", data=csv, file_name="rankings.csv")
    
    for index, row in df.iterrows():
        with st.expander(f"📊 {row['Score']}% — {row['Name']}"):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("**🏢 Company Review**")
                st.warning(row["Recruiter_Notes"])
            with c2:
                st.markdown("**🎓 Applicant Guidance**")
                st.info(row["Applicant_Notes"])
            
            if st.button("Shortlist", key=f"sl_{index}"):
                st.success(f"Shortlisted {row['Name']}!")
                st.balloons()
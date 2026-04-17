import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
import pandas as pd

# --- Page Config ---
st.set_page_config(page_title="HireSync AI", layout="wide")

# --- UI Header ---
st.title("✨ HireSync AI: Recruiter Dashboard")
st.subheader("Dual-View Analysis: Internal Review & Applicant Guidance")

# --- Sidebar ---
with st.sidebar:
    st.header("Settings")
    # FIX: Looks for secret key first (for deployment), then falls back to manual input
    if "GEMINI_API_KEY" in st.secrets:
        api_key = st.secrets["GEMINI_API_KEY"]
        st.success("✅ System Key Active")
    else:
        api_key = st.text_input("Enter Gemini API Key", type="password")
        st.info("Get your key from [Google AI Studio](https://aistudio.google.com/)")
    
    st.markdown("---")
    if st.button("🔄 Reset All Data"):
        st.session_state.analysis_results = []
        st.session_state.shortlist = []
        st.rerun()

# --- Helper Functions ---
def extract_text_from_pdf(file):
    try:
        reader = PdfReader(file)
        text = "".join([page.extract_text() for page in reader.pages if page.extract_text()])
        return text
    except Exception as e:
        return f"Error: {e}"

def get_gemini_score(resume_text, jd, api_key):
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel("models/gemini-2.5-flash")
        
        prompt = f"""
        Analyze Resume vs JD. 
        Provide a numeric score (0-100), an internal review for the company, and improvement guidance for the applicant.
        Return STRICTLY in this format: Score | Internal Review | Applicant Guidance
        
        JD: {jd}
        Resume: {resume_text}
        """
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        return f"0 | Error: {str(e)} | N/A"

# --- Memory Management (Session State) ---
if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = []

# --- Input Section ---
job_description = st.text_area("📋 Paste Job Description (JD):", height=150, placeholder="What are you looking for in a candidate?")
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
                if text.strip():
                    analysis = get_gemini_score(text, job_description, api_key)
                    
                    # Robust Parsing
                    try:
                        if "|" in analysis:
                            parts = analysis.split("|")
                            score_digits = ''.join(filter(str.isdigit, parts[0]))
                            score = int(score_digits) if score_digits else 0
                            
                            temp_results.append({
                                "Name": file.name,
                                "Score": score,
                                "Recruiter_Notes": parts[1].strip() if len(parts) > 1 else "Analysis failed",
                                "Applicant_Notes": parts[2].strip() if len(parts) > 2 else "No guidance provided"
                            })
                    except:
                        continue
            progress_bar.progress((i + 1) / len(uploaded_files))
        
        # Save to memory!
        st.session_state.analysis_results = temp_results

# --- Display Results from Memory ---
if st.session_state.analysis_results:
    st.markdown("---")
    
    # Sort data by highest score
    df = pd.DataFrame(st.session_state.analysis_results).sort_values(by="Score", ascending=False)
    
    # Global CSV Download
    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button("📥👉 Download Full Ranking (CSV)", data=csv, file_name="hiresync_rankings.csv", mime="text/csv")
    
    st.write("### Candidate Rankings")

    for index, row in df.iterrows():
        # Expanders allow for full text visibility
        with st.expander(f"📊 {row['Score']}% — {row['Name']}"):
            c1, c2 = st.columns(2)
            with c1:
                st.markdown("#### 🏢 Company Internal Review")
                st.warning(row["Recruiter_Notes"])
            with c2:
                st.markdown("#### 🎓 Applicant Guidance")
                st.info(row["Applicant_Notes"])
            
            # Interactive Buttons (Functioning via Session State)
            col_btn1, col_btn2 = st.columns([1, 4])
            with col_btn1:
                if st.button("Shortlist", key=f"sl_{index}"):
                    st.success(f"Shortlisted {row['Name']}!")
                    st.balloons()

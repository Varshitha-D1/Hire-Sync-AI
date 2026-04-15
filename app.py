import streamlit as st
import google.generativeai as genai
from PyPDF2 import PdfReader
import pandas as pd
import os

# --- Page Config ---
st.set_page_config(page_title="HireSync AI - Recruiter Dashboard", layout="wide")

# --- UI Header ---
st.title("🎯 HireSync AI: Recruiter Dashboard")
st.subheader("Upload resumes to rank candidates against your Job Description")

# --- Sidebar: Configuration ---
with st.sidebar:
    st.header("Settings")
    # Using password type so your key isn't visible on screen
    api_key = st.text_input("Enter Gemini API Key", type="password")
    
    st.info("Get your key from [Google AI Studio](https://aistudio.google.com/)")
    st.markdown("---")
    st.caption("v1.2 - Fixed Model Connection Error")

# --- Helper Functions ---
def extract_text_from_pdf(file):
    """Extracts all text from a PDF file."""
    try:
        reader = PdfReader(file)
        text = ""
        for page in reader.pages:
            content = page.extract_text()
            if content:
                text += content
        return text
    except Exception as e:
        return f"Error reading PDF: {e}"

def get_gemini_score(resume_text, jd, api_key):
    """Calls Gemini API with explicit model pathing to avoid 404 errors."""
    try:
        # Configure inside the function to ensure the session is active
        genai.configure(api_key=api_key)
        
        # Using the explicit production model path
        model = genai.GenerativeModel("models/gemini-2.5-flash")
        
        prompt = f"""
        You are an expert HR recruitment tool. 
        Compare the Resume provided below with the Job Description (JD).
        1. Score the candidate out of 100 based on how well they match the JD.
        2. Provide a 1-sentence summary of their key strengths or gaps.
        
        Return the result STRICTLY in this format: Score | Summary
        
        JD: {jd}
        Resume: {resume_text}
        """
        
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        # Catching the specific error to display in the table
        return f"0 | Error: {str(e)}"

# --- Input Section ---
job_description = st.text_area("Paste the Job Description (JD) here:", height=200, placeholder="Enter skills, experience, and role requirements...")
uploaded_files = st.file_uploader("Upload Resumes (PDF)", type="pdf", accept_multiple_files=True)

# --- Processing Section ---
if st.button("Rank Resumes"):
    if not api_key:
        st.error("Please provide an API key in the sidebar.")
    elif not job_description:
        st.warning("Please paste a Job Description first.")
    elif not uploaded_files:
        st.warning("Please upload at least one PDF resume.")
    else:
        results = []
        progress_bar = st.progress(0)
        
        # Process each file
        for i, file in enumerate(uploaded_files):
            with st.spinner(f"Analyzing {file.name}..."):
                # 1. Extract
                text = extract_text_from_pdf(file)
                
                # 2. Analyze
                if text.strip():
                    analysis = get_gemini_score(text, job_description, api_key)
                else:
                    analysis = "0 | Error: Could not extract text from PDF."
                
                # 3. Parse and Clean Data
                try:
                    if "|" in analysis:
                        parts = analysis.split("|")
                        score_str = parts[0].strip()
                        # Extract only the digits from the score part
                        score_digits = ''.join(filter(str.isdigit, score_str))
                        score = int(score_digits) if score_digits else 0
                        summary = parts[1].strip()
                    else:
                        score = 0
                        summary = analysis # Show the error message if no pipe found
                    
                    results.append({
                        "Candidate Name": file.name,
                        "Match Score": score,
                        "Summary": summary
                    })
                except Exception as e:
                    results.append({
                        "Candidate Name": file.name, 
                        "Match Score": 0, 
                        "Summary": f"Parsing Error: {str(e)}"
                    })
            
            # Update progress
            progress_bar.progress((i + 1) / len(uploaded_files))

        # --- Display Results ---
        if results:
            st.success("Analysis Complete!")
            df = pd.DataFrame(results)
            # Sort by highest score
            df = df.sort_values(by="Match Score", ascending=False)
            
            # Display as a clean, interactive table
            st.dataframe(df, use_container_width=True, hide_index=True)
            
            # Option to download as CSV
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download Results as CSV",
                data=csv,
                file_name="resume_rankings.csv",
                mime="text/csv",
            )
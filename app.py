import streamlit as st
import pdfplumber
from groq import Groq
import re

# 1. Setup Page Config
st.set_page_config(page_title="ATS Resume Co-Pilot", page_icon="🎯", layout="wide")

# 2. Sidebar Settings
with st.sidebar:
    st.title("🛡️ Admin Settings")
    api_key = st.text_input("Enter Groq API Key", type="password")
    st.info("Models: Llama-3.3-70b (Recommended)")
    model_choice = "llama-3.3-70b-versatile"
    
    st.divider()
    st.markdown("### 💡 How to use with friends:")
    st.write("1. Upload a PDF Resume.")
    st.write("2. Paste a Job Description.")
    st.write("3. Click 'Initial Analyze'.")
    st.write("4. Select any 'Hidden Skills' you have to boost your score.")

# 3. Helper Functions
def extract_pdf_text(uploaded_file):
    try:
        with pdfplumber.open(uploaded_file) as pdf:
            text = ""
            for page in pdf.pages:
                content = page.extract_text(layout=True)
                if content:
                    text += content + "\n\n"
        return text if text.strip() else "Error: PDF appears to be empty or an image."
    except Exception as e:
        return f"Error reading PDF: {e}"

def call_groq(prompt, api_key):
    try:
        client = Groq(api_key=api_key)
        completion = client.chat.completions.create(
            model=model_choice,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2,
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"API Error: {e}"

# 4. Main UI
st.title("🎯 ATS Resume Co-Pilot")
st.subheader("Smart Analysis & Ethical Tailoring for Engineers")

# Session State Initialization
if "initial_analysis" not in st.session_state:
    st.session_state.initial_analysis = None
if "resume_text" not in st.session_state:
    st.session_state.resume_text = ""
if "new_score" not in st.session_state:
    st.session_state.new_score = 0

col1, col2 = st.columns(2)
with col1:
    resume_file = st.file_uploader("📂 Upload Resume (PDF)", type="pdf")
with col2:
    job_desc = st.text_area("📝 Paste Job Description", height=200, placeholder="Paste the full JD requirements here...")

# 5. STEP 1: INITIAL ANALYSIS
if st.button("🔍 Step 1: Run Initial Match Analysis", use_container_width=True):
    if not api_key:
        st.error("Please provide a Groq API Key in the sidebar.")
    elif not resume_file or not job_desc:
        st.warning("Please upload both a Resume and a Job Description.")
    else:
        with st.status("Analyzing Skill Alignment...", expanded=True) as status:
            resume_data = extract_pdf_text(resume_file)
            if "Error" in resume_data:
                st.error(resume_data)
            else:
                st.session_state.resume_text = resume_data
                analysis_prompt = f"""
                Act as a Technical Recruiter. Compare the Resume to the JD.
                Format exactly:
                ---
                SCORE: [0-100]%
                ---
                MISSING: [Skill A, Skill B, Skill C]
                
                JD: {job_desc}
                RESUME: {resume_data}
                """
                st.session_state.initial_analysis = call_groq(analysis_prompt, api_key)
                status.update(label="Analysis Complete!", state="complete")

# 6. STEP 2: INTERACTIVE SKILL SELECTOR
if st.session_state.initial_analysis:
    try:
        parts = st.session_state.initial_analysis.split("---")
        score_val = int(re.search(r'\d+', parts[1]).group())
        missing_skills = [s.strip() for s in parts[2].replace("MISSING:", "").split(",") if s.strip()]
        
        st.divider()
        st.metric("Initial ATS Match Score", f"{score_val}%")

        if score_val < 80:
            st.info("⚠️ **Match Score below 80%**")
            st.markdown("Do you have experience in any of these areas that wasn't mentioned in your PDF? Select them to update your score:")
            
            # Checkbox Grid
            confirmed_skills = []
            cols = st.columns(3)
            for i, skill in enumerate(missing_skills):
                with cols[i % 3]:
                    if st.checkbox(skill, key=f"skill_{i}"):
                        confirmed_skills.append(skill)
            
            if st.button("🔄 Update Score & Check Eligibility", use_container_width=True):
                # Calculate bonus (approx 5% per relevant skill found)
                bonus = len(confirmed_skills) * 6 
                updated_score = min(score_val + bonus, 100)
                st.session_state.new_score = updated_score
                st.session_state.confirmed_skills = confirmed_skills
                
                if updated_score >= 80:
                    st.success(f"🎉 New Score: {updated_score}%! You are now eligible for tailoring.")
                else:
                    st.error(f"Score is now {updated_score}%. Still below the 80% threshold for professional tailoring.")
        else:
            st.session_state.new_score = score_val
            st.session_state.confirmed_skills = []
            st.success("🔥 High Match! You are eligible for instant tailoring.")

    except Exception as e:
        st.error("Could not parse analysis. Please try again.")

# 7. STEP 3: FINAL TAILORING
if st.session_state.new_score >= 80:
    st.divider()
    if st.button("🚀 Step 3: Generate Optimized Resume", use_container_width=True):
        with st.spinner("Crafting your tailored resume..."):
            extra_skills = ", ".join(st.session_state.get('confirmed_skills', []))
            final_prompt = f"""
            Rewrite this resume into a professional ATS-friendly format. 
            Integrate these additional confirmed skills: {extra_skills}.
            
            FORMATTING:
            - Use ## for sections and ### for job titles.
            - Use bullet points for all experience.
            - **BOLD** all JD-relevant keywords.
            - Start with a strong Professional Summary.
            
            RESUME: {st.session_state.resume_text}
            JD: {job_desc}
            """
            final_resume = call_groq(final_prompt, api_key)
            st.markdown("### ✅ Your Tailored Resume")
            st.markdown(final_resume)
            st.download_button("📥 Download Resume (.md)", final_resume, file_name="Tailored_Resume.md")

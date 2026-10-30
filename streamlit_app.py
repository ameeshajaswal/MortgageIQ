# streamlit_app.py

import os
import streamlit as st
from mortgage_crew import MortgageAdvisorSystem

# ---------- Paths & setup for uploads ----------

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploaded_docs")

# Make sure the folder exists so document_loader_tool can see it
os.makedirs(UPLOAD_DIR, exist_ok=True)

st.set_page_config(page_title="AI Mortgage Advisor", page_icon="🏠")
st.title("🏠 AI Mortgage Advisor Prototype")
st.caption(
    "Digital mortgage broker with eligibility, products, paperwork, "
    "customer intelligence and introspection."
)

# ---------- Session state ----------

if "advisor_system" not in st.session_state:
    st.session_state.advisor_system = MortgageAdvisorSystem(verbose=True)

if "messages" not in st.session_state:
    # Each message: {"role": "user" | "assistant", "content": str}
    st.session_state.messages = []

if "uploaded_files_meta" not in st.session_state:
    # Store simple metadata so the agents know what exists
    st.session_state.uploaded_files_meta = []


# ---------- Sidebar ----------

with st.sidebar:
    st.subheader("Session controls")
    if st.button("🔄 Reset conversation"):
        st.session_state.messages = []
        st.session_state.uploaded_files_meta = []
        # Also clear uploaded_docs folder
        try:
            for name in os.listdir(UPLOAD_DIR):
                path = os.path.join(UPLOAD_DIR, name)
                if os.path.isfile(path):
                    os.remove(path)
        except Exception as e:
            st.warning(f"Could not clear uploaded_docs: {e}")
        st.rerun()

    st.markdown("---")
    
    # ---------- Document upload (in sidebar like ChatGPT/Claude) ----------
    st.subheader("📎 Upload Documents")
    
    uploaded_files = st.file_uploader(
        "Pay stubs, employment letters, IDs, bank statements, etc.",
        type=["pdf"],
        accept_multiple_files=True,
        key="file_uploader"
    )
    
    saved_file_names = []
    
    if uploaded_files:
        for f in uploaded_files:
            # Save to uploaded_docs/ so document_loader_tool can read it
            save_path = os.path.join(UPLOAD_DIR, f.name)
            
            with open(save_path, "wb") as out_file:
                out_file.write(f.getbuffer())
            
            saved_file_names.append(f.name)
        
        # Track in session metadata (for context to agents)
        for name in saved_file_names:
            if {"name": name, "saved_in": "uploaded_docs"} not in st.session_state.uploaded_files_meta:
                st.session_state.uploaded_files_meta.append({"name": name, "saved_in": "uploaded_docs"})
    
    # Show currently uploaded files
    existing_pdfs = [fn for fn in os.listdir(UPLOAD_DIR) if fn.lower().endswith(".pdf")]
    
    if existing_pdfs:
        st.markdown("**Uploaded files:**")
        for pdf in existing_pdfs:
            st.text(f"✓ {pdf}")
    else:
        st.caption("No documents uploaded yet")
    
    st.markdown("---")
    
    st.markdown(
        """
        **How to test:**
        1. Upload documents using the file uploader above
        2. Ask about eligibility: *"Can I qualify for a 500k mortgage?"*  
        3. Ask about your documents: *"Am I eligible based on the documents provided?"*
        """
    )

# Build a summary of everything in uploaded_docs
existing_pdfs = [fn for fn in os.listdir(UPLOAD_DIR) if fn.lower().endswith(".pdf")]
uploaded_summary = ""

if existing_pdfs:
    uploaded_summary = (
        "User has uploaded the following PDFs so far (stored in uploaded_docs/): "
        + ", ".join(existing_pdfs)
    )


# ---------- Chat history ----------

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])


# ---------- Chat input ----------

prompt = st.chat_input("Ask about eligibility, products, or applying...")

if prompt:
    # 1) Show user message
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2) Build a richer message for the backend:
    #    include a system note about uploaded docs, if any.
    full_message = prompt
    if uploaded_summary:
        full_message += "\n\n[System note for backend: " + uploaded_summary + "]"

    # 3) Call the advisor system
    with st.chat_message("assistant"):
        with st.spinner("Thinking about your situation..."):
            advisor: MortgageAdvisorSystem = st.session_state.advisor_system
            reply = advisor.run(full_message)

        st.markdown(reply)

    # 4) Store assistant reply
    st.session_state.messages.append({"role": "assistant", "content": reply})

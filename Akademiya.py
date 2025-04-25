import os
import re
import base64

import streamlit as st
from dotenv import load_dotenv
import fitz  # PyMuPDF

# --- Page Config ---
st.set_page_config(
    page_title="Akademiya Upload",
    page_icon="🎓",
    layout="centered"
)

def load_css(file_path):
    """Reads a CSS file and returns its content."""
    try:
        with open(file_path) as f:
            return f.read()
    except FileNotFoundError:
        st.error(f"CSS file not found at {file_path}")
        return ""

css_content = load_css("styles.css")
if css_content:
    st.markdown(f"<style>{css_content}</style>", unsafe_allow_html=True)

# --- Environment Loading ---
load_dotenv()


# --- Constants ---
MAX_WORDS = 7500  # Max words to process from PDF


# --- Helper Functions ---
def show_pdf_from_bytes(pdf_bytes):
    try:
        base64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
        # Display PDF using an iframe is necessary in Streamlit
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="100%" height="500px" type="application/pdf"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error displaying PDF: {e}")


def extract_text_from_bytes(pdf_bytes):
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
        return ""


def clean_extracted_text(text):
    # Basic cleaning: Replace multiple whitespace chars with single space
    cleaned_text = re.sub(r'\s+', ' ', text)
    return cleaned_text.strip()


# --- Session State Initialization ---
def initialize_state():
    state_keys = [
        'uploaded_bytes', 'extracted_text', 'gpt_response_raw',
        'summary', 'key_points', 'flashcards', 'quiz',
        'parsing_failed'
    ]
    for key in state_keys:
        if key not in st.session_state:
            st.session_state[key] = None

initialize_state()


# --- Main Page UI and Logic ---
st.title("Akademiya Content Generation")
st.header("1. Upload Your PDF")

# File Uploader
uploaded = st.file_uploader(
    "Select a PDF file:", 
    type=["pdf"], 
    key="pdf_uploader",
    label_visibility="collapsed"
)

# Process uploaded file
if uploaded:
    uploaded_bytes_value = uploaded.getvalue()
    if st.session_state.get('uploaded_bytes') != uploaded_bytes_value:
        st.session_state['uploaded_bytes'] = uploaded_bytes_value
        
        keys_to_reset = [
            'extracted_text', 'gpt_response_raw', 'summary', 
            'key_points', 'flashcards', 'quiz'
        ]
        for key in keys_to_reset:
            st.session_state[key] = None 
            
        st.session_state['parsing_failed'] = False

        # Attempt text extraction
        with st.spinner("Processing PDF..."):
            raw_text = extract_text_from_bytes(st.session_state['uploaded_bytes'])
        if raw_text:
            cleaned_text = clean_extracted_text(raw_text)
            words = cleaned_text.split()
            if len(words) > MAX_WORDS:
                st.warning(f"PDF is long; only the first {MAX_WORDS} words ({len(words)} provided) will be processed.")
                cleaned_text = ' '.join(words[:MAX_WORDS])
            st.session_state['extracted_text'] = cleaned_text
            st.success("PDF processed successfully!")
        else:
            st.error("Could not extract text from the PDF.")
            st.session_state['uploaded_bytes'] = None 

# Display Previews (only if upload was successful)
if st.session_state.get('uploaded_bytes'):
    st.subheader("PDF Preview:")
    show_pdf_from_bytes(st.session_state['uploaded_bytes'])

    if st.session_state.get('extracted_text'):
         with st.expander("View Extracted Text"):
              # Use disabled text_area for preview
              st.text_area("Text Preview", st.session_state['extracted_text'], height=200, disabled=True, label_visibility="collapsed")
    else:
         st.warning("No text was extracted to preview.")

# Navigation Button
if st.session_state.get('extracted_text'):
    st.divider()
    st.header("2. Configure & Generate")
    # Use full width button for primary navigation
    if st.button("Continue to Configuration ->", use_container_width=True):
        try:
            # Use Streamlit's preferred navigation method
            st.switch_page("pages/1_Configure_Generation.py")
        except Exception as e:
            st.error(f"Navigation failed (requires Streamlit 1.28+): {e}")
            st.info("Please navigate using the sidebar.")

else:
    # Show info if no PDF is uploaded yet
    st.info("Upload a PDF file to begin the process.")

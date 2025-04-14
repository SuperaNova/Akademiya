import os
import re
import base64

import streamlit as st
from dotenv import load_dotenv
import fitz  # PyMuPDF
from openai import OpenAI

# Load environment variables
load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

MAX_WORDS = 7500  # around 8k tokens

# Function to get a response from GPT
def get_gpt_response(prompt):
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-nano",  # 4.1 cheapest model rn
            messages=[
                {
                    "role": "system",
                    "content": """
                    You are an educational assistant.
                    Given the following text:
                    - First, provide a concise single-paragraph summary of the content.
                    - Then, list 3–7 key points or notes as bullet points, focusing on the most important details.
                    - Finally, create 3–5 flashcards. Each flashcard MUST have:
                      - a clear question,
                      - 3 or 4 multiple-choice options labeled a), b), c), (and d) if needed),
                      - the correct answer indicated (e.g., “Correct answer: a)” at the end of each flashcard).
                    Format your response with clear section headers: Summary, Key Points, and Flashcards.
                    """
                },
                {"role": "user", "content": prompt}
            ],
            max_tokens=1000  # Max Output Token Count
        )
        output = response.choices[0].message.content.strip()
        in_tokens = getattr(response.usage, 'prompt_tokens', None)
        out_tokens = getattr(response.usage, 'completion_tokens', None)
        total = getattr(response.usage, 'total_tokens', None)
        return output, in_tokens, out_tokens, total
    except Exception as e:
        return f"Error: {e}", None, None, None

# Display PDF in Streamlit
def show_pdf_from_bytes(pdf_bytes):
    try:
        base64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="700" height="1000" type="application/pdf"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error displaying PDF: {e}")

# Extract text from PDF bytes
def extract_text_from_bytes(pdf_bytes):
    try:
        # Open PDF stream
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    except Exception as e:
        st.error(f"Error reading PDF: {e}")
        return ""

# Clean extracted text
def clean_extracted_text(text):
    # Remove multiple spaces, newlines, and trim
    cleaned_text = re.sub(r'\s+', ' ', text)
    return cleaned_text.strip()

st.title("Akademiya Quiz Generation Demo")

# Upload PDF file
uploaded = st.file_uploader("Upload a PDF file:", type=["pdf"])

if uploaded:
    uploaded_bytes = uploaded.read()
    # Show PDF
    st.subheader("Uploaded PDF:")
    show_pdf_from_bytes(uploaded_bytes)

    # Extract and clean text
    raw_text = extract_text_from_bytes(uploaded_bytes)
    if raw_text:
        cleaned_text = clean_extracted_text(raw_text)
        st.subheader("Cleaned Extracted Text from PDF:")
        st.text_area("Extracted and Cleaned Text", cleaned_text, height=300)

        # 8k max tokens
        words = cleaned_text.split()
        if len(words) > MAX_WORDS:
            st.warning(f"PDF is long; only the first {MAX_WORDS} words ({len(words)} provided) will be processed.")
            cleaned_text = ' '.join(words[:MAX_WORDS])

        st.write(f"Input words sent to GPT: {len(cleaned_text.split())}")

        response, in_tokens, out_tokens, total = get_gpt_response(cleaned_text)
        if response:
            st.subheader("GPT Response (Summary, Notes, Flashcards):")
            st.write(response)
            if in_tokens is not None and out_tokens is not None and total is not None:
                st.info(f"Token usage — Input: {in_tokens}, Output: {out_tokens}, Total: {total}")
        else:
            st.warning("No valid response from GPT.")
    else:
        st.warning("No text could be extracted from the uploaded PDF.")

# Rerun button
if st.button("🔁 Rerun"):
    st.experimental_rerun()
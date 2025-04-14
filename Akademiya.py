import streamlit as st
import base64
import fitz  # PyMuPDF
from io import BytesIO
import openai
from dotenv import load_dotenv
import os
import re

# Load environment variables
load_dotenv()
openai.api_key = os.getenv("OPENAI_API_KEY")

# Function to get a response from GPT
def get_gpt_response(prompt):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4.1-nano",
            messages=[
                {
                    "role": "system",
                    "content": """
                        Read the following text carefully. Then, based on the content, summarize it in a short paragraph.
                        Create key points or notes for easy reference, and make short flashcards for review.
                        Each flashcard should consist of a question and multiple choices (a, b, etc.) as possible answers.
                    """
                },
                {"role": "user", "content": prompt}
            ],
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"Error: {e}"

# Function to split large texts into chunks
def split_text_into_chunks(text, max_chunk_size=1000):
    words = text.split()
    chunks = []
    current_chunk = []
    current_size = 0

    for word in words:
        word_size = len(word.split())  # Approximate token count
        if current_size + word_size > max_chunk_size:
            chunks.append(' '.join(current_chunk))
            current_chunk = [word]
            current_size = word_size
        else:
            current_chunk.append(word)
            current_size += word_size

    if current_chunk:
        chunks.append(' '.join(current_chunk))
    return chunks

# display PDF
def show_pdf_from_bytes(pdf_bytes):
    try:
        base64_pdf = base64.b64encode(pdf_bytes).decode("utf-8")
        pdf_display = f'<iframe src="data:application/pdf;base64,{base64_pdf}" width="700" height="1000" type="application/pdf"></iframe>'
        st.markdown(pdf_display, unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Error displaying PDF: {e}")

# Function to extract and clean text from PDF bytes
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

# Function to clean extracted text
def clean_extracted_text(text):
    # Remove multiple spaces, newlines, and trim
    cleaned_text = re.sub(r'\s+', ' ', text)
    return cleaned_text.strip()

st.title("Akademiya Quiz Generation Demo")

# Initialize chat history
if 'messages' not in st.session_state:
    st.session_state['messages'] = []

# Display chat history
for message in st.session_state['messages']:
    role = message['role'].capitalize()
    content = message['content']
    if role == "User":
        st.markdown(f"**You:** {content}")
    else:
        st.markdown(f"**Bot:** {content}")

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

        # Split cleaned text into chunks for GPT
        chunks = split_text_into_chunks(cleaned_text)
        responses = []

        # Send chunks to GPT
        for chunk in chunks:
            response = get_gpt_response(chunk)
            responses.append(response)

        # Combine responses
        final_response = " ".join(responses)

        st.subheader("GPT Response (Summary, Notes, Flashcards):")
        st.write(final_response)
    else:
        st.warning("No text could be extracted from the uploaded PDF.")

# User input for conversation
user_input = st.text_input("Your message:", key="user_input")

if user_input:
    # Add user message
    st.session_state['messages'].append({"role": "user", "content": user_input})
    # Get bot response
    bot_response = get_gpt_response(user_input)
    st.session_state['messages'].append({"role": "bot", "content": bot_response})
    # Display latest exchange
    st.markdown(f"**You:** {user_input}")
    st.markdown(f"**Bot:** {bot_response}")

# Rerun button
if st.button("🔁 Rerun"):
    st.experimental_rerun()
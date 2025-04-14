import streamlit as st
import openai
from dotenv import load_dotenv
import os

# Load environment variables from .env file
load_dotenv()

# Set up OpenAI API key
openai.api_key = os.getenv("OPENAI_API_KEY")

# Function to get a response from OpenAI's GPT
def get_gpt_response(prompt):
    try:
        # Using the new ChatCompletion method
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # or "gpt-4" depending on your API access
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ]
        )
        return response['choices'][0]['message']['content'].strip()
    except Exception as e:
        return f"Error: {e}"

# Streamlit app layout
st.title("Akademiya Chatbot")

# Create chat history to store messages
if 'messages' not in st.session_state:
    st.session_state['messages'] = []

# Display previous conversation history
for message in st.session_state['messages']:
    st.write(f"{message['role'].capitalize()}: {message['content']}")

# User input text box
user_input = st.text_input("You: ", "")

# When the user submits a message
if user_input:
    # Append user message to chat history
    st.session_state['messages'].append({"role": "user", "content": user_input})
    
    # Get GPT's response
    response = get_gpt_response(user_input)
    
    # Append bot message to chat history
    st.session_state['messages'].append({"role": "bot", "content": response})
    
    # Display the response
    st.write(f"Bot: {response}")

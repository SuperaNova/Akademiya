import os
import re
import json
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# --- Environment & Client Initialization ---

def initialize_openai_client():
    """Loads environment variables and initializes the OpenAI client.
    
    Returns:
        OpenAI client object or None if initialization fails.
    """
    load_dotenv()
    client = None
    try:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            # Use st.warning here as error might be shown on page anyway
            st.warning("OpenAI API key not found in .env. Features requiring API calls will be disabled.")
            return None
        client = OpenAI(api_key=api_key)
        return client
    except Exception as e:
        st.error(f"Failed to initialize OpenAI client: {e}")
        return None

# --- Core Content Generation ---

def get_gpt_response(client, user_prompt, system_prompt_content):
    """Calls the OpenAI API to generate content based on prompts.

    Args:
        client: The initialized OpenAI client.
        user_prompt: The user's input text (e.g., extracted PDF content).
        system_prompt_content: The system prompt defining the task and format.

    Returns:
        The AI's response content as a string, or None if an error occurs.
    """
    if not client:
        st.error("OpenAI client not available for generation.")
        return None
    
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-nano", 
            messages=[
                {"role": "system", "content": system_prompt_content},
                {"role": "user", "content": user_prompt} 
            ],
            max_tokens=2048 
        )
        output = response.choices[0].message.content.strip()
        return output
    except Exception as e:
        st.error(f"Error calling OpenAI API for generation: {e}")
        return None

# --- JSON Parsing Helper ---

def parse_json_response(response_text):
    """Attempts to parse a JSON object from the AI's response text.
    
    Handles potential markdown code fences.
    
    Args:
        response_text: The raw string response from the AI.
        
    Returns:
        A dictionary parsed from JSON, or None if parsing fails.
    """
    parsed_data = None
    error_message = None
    try:
        # Try finding ```json ... ``` block first
        match = re.search(r'```json\n(.*?)\n```', response_text, re.DOTALL)
        if match:
            json_string = match.group(1)
        else:
            # If no block, assume the whole string might be JSON, or find first/last brace
            first_brace = response_text.find('{')
            last_brace = response_text.rfind('}')
            if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
                json_string = response_text[first_brace:last_brace+1]
            else: # Fallback if no obvious JSON structure found
                json_string = response_text 

        parsed_data = json.loads(json_string)
        
        # Basic validation (can be expanded based on expected structure)
        if isinstance(parsed_data, dict):
            return parsed_data
        else:
            error_message = "Parsed data is not a valid JSON object (dictionary)."
            
    except json.JSONDecodeError as json_err:
        error_message = f"Failed to decode JSON: {json_err}"
    except Exception as e:
        error_message = f"An unexpected error occurred during JSON parsing: {e}"

    # If parsing failed at any point
    st.error(f"JSON Parsing Error: {error_message}")
    st.warning("Raw AI Response (relevant part for parsing):")
    st.text_area("Raw Text", json_string if 'json_string' in locals() else response_text, height=150, key="json_parsing_error_raw")
    return None

# --- Flashcard/Quiz Item Regeneration ---

def regenerate_item(client, item_type, original_text_context, item_to_regenerate):
    """Generates a new, different flashcard or quiz question based on context.

    Args:
        client: The initialized OpenAI client.
        item_type (str): 'flashcard' or 'quiz question'.
        original_text_context (str): The source text context.
        item_to_regenerate (dict): The original item dictionary.

    Returns:
        A dictionary with the new item data, or None if failed.
    """
    if not client:
        st.error(f"Cannot regenerate {item_type}: OpenAI client not available.")
        return None
    
    original_question = item_to_regenerate.get('question', '')
    system_prompt = f"""You are an educational assistant improving {item_type}s.

Original Context (Excerpt): {original_text_context[:1000]}...
Original Question: {original_question}

Your task is to create a NEW and DIFFERENT {item_type} question based on the provided context. The new question should cover a similar topic or concept if possible, but be distinct from the original question.

Your output MUST be a single JSON object with keys: 'question', 'options' (an object with 'a', 'b', 'c', maybe 'd'), and 'answer' (the key of the correct option).
Example: {{"question": "Sample new question?", "options": {{"a": "Opt A", "b": "Opt B"}}, "answer": "a"}}
Do NOT include any text outside the single JSON object.
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[{"role": "system", "content": system_prompt}],
            max_tokens=300 # Smaller max tokens for regeneration
        )
        response_text = response.choices[0].message.content.strip()
        
        new_item_data = parse_json_response(response_text)
        
        # Validate structure specifically for flashcard/quiz items
        if new_item_data and all(k in new_item_data for k in ('question', 'options', 'answer')):
            return new_item_data
        elif new_item_data:
             st.error(f"Regenerated {item_type} JSON missing required keys (question, options, answer).")
             return None
        else: 
             # parse_json_response already showed an error
             return None

    except Exception as e:
        st.error(f"Error during {item_type} regeneration API call: {e}")
        return None

# --- Flashcard/Quiz Item Addition ---

def add_new_item(client, item_type, original_text_context, existing_items):
    """Generates one new, distinct flashcard or quiz question.

    Args:
        client: The initialized OpenAI client.
        item_type (str): 'flashcard' or 'quiz question'.
        original_text_context (str): The source text context.
        existing_items (list): List of existing item dictionaries.

    Returns:
        A dictionary with the new item data, or None if failed.
    """
    if not client:
        st.error(f"Cannot add {item_type}: OpenAI client not available.")
        return None

    existing_q_str = "\n".join([f"- {q.get('question', '')}" for q in existing_items])
    
    system_prompt = f"""You are an educational assistant creating {item_type}s.

Context (Excerpt): {original_text_context[:2000]}...

Existing {item_type.capitalize()} Questions (Do not repeat these exact questions):
{existing_q_str}

Your task is to create ONE NEW, DISTINCT {item_type} based on the provided context that is different from the existing ones.

Your output MUST be a single JSON object with keys: 'question', 'options' (an object with 'a', 'b', 'c', maybe 'd'), and 'answer' (the key of the correct option).
Example: {{"question": "Sample new question?", "options": {{"a": "Opt A", "b": "Opt B"}}, "answer": "a"}}
Do NOT include any text outside the single JSON object.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-nano",
            messages=[{"role": "system", "content": system_prompt}],
            max_tokens=300 # Smaller max tokens for addition
        )
        response_text = response.choices[0].message.content.strip()
        
        new_item_data = parse_json_response(response_text)
        
        # Validate structure
        if new_item_data and all(k in new_item_data for k in ('question', 'options', 'answer')):
            return new_item_data
        elif new_item_data:
             st.error(f"Newly generated {item_type} JSON missing required keys (question, options, answer).")
             return None
        else:
             # parse_json_response already showed an error
             return None
             
    except Exception as e:
        st.error(f"Error during new {item_type} generation API call: {e}")
        return None 
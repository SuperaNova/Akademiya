import os
import re
import json
import streamlit as st
from dotenv import load_dotenv
from openai import OpenAI

# --- Default Constants ---
DEFAULT_MODEL = "gpt-4o-mini" # Or your preferred default model
DEFAULT_TEMP = 0.7

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

# --- Prompt Construction ---

def construct_prompt(content_types, focus_instruction=None):
    """Constructs the system prompt for the main content generation task.

    Args:
        content_types (list): A list of strings indicating the desired content types 
                              (e.g., ["Summary", "Key Points", "Flashcards", "Quiz"]).
        focus_instruction (str, optional): Specific instructions to focus the generation.
                                           Defaults to None.

    Returns:
        str: The constructed system prompt.
    """
    prompt_parts = [
        "You are an expert educational assistant. Your task is to process the provided text and generate educational content based on the user's request.",
        "Please generate the following content types:",
        ""
    ]

    # Define JSON structure based on requested types
    json_structure_parts = []
    if "Summary" in content_types:
        prompt_parts.append("- A concise summary of the text.")
        json_structure_parts.append('  "summary": "Your concise summary here..."')
    if "Key Points" in content_types:
        prompt_parts.append("- A list of key points, where each point includes a brief description or elaboration.")
        json_structure_parts.append('  "key_points": [{"point": "Key Concept 1", "description": "Brief explanation of concept 1..."}, {"point": "Key Concept 2", "description": "Brief explanation of concept 2..."}, ...]')
    if "Flashcards" in content_types:
        prompt_parts.append("- A set of flashcards (question/answer pairs suitable for learning).")
        json_structure_parts.append('  "flashcards": [{"question": "Q1", "answer": "A1"}, {"question": "Q2", "answer": "A2"}, ...]')
    if "Quiz" in content_types:
        prompt_parts.append("- A multiple-choice quiz based on the text.")
        json_structure_parts.append('  "quiz": [{"question": "Q1", "options": {"a": "OptA", "b": "OptB", "c": "OptC"}, "answer": "a"}, ...]')

    prompt_parts.append("")
    prompt_parts.append("Your output MUST be a single valid JSON object containing keys for ONLY the requested content types.")
    prompt_parts.append("Example JSON Structure:")
    prompt_parts.append("{")
    prompt_parts.extend([part + "," for part in json_structure_parts[:-1]]) # Add comma to all but last
    if json_structure_parts:
        prompt_parts.append(json_structure_parts[-1]) # Add last part without comma
    prompt_parts.append("}")
    prompt_parts.append("")
    prompt_parts.append("Ensure the JSON is well-formed. Do NOT include any text or explanations outside of the main JSON object.")

    # Add focus instruction if provided
    if focus_instruction and focus_instruction.strip():
        prompt_parts.append("")
        prompt_parts.append("--- Focus Instruction ---")
        prompt_parts.append(f"Please pay special attention to the following when generating the content: {focus_instruction.strip()}")
        prompt_parts.append("-----------------------")

    return "\n".join(prompt_parts)


# --- Core Content Generation ---

def get_gpt_response(client, user_prompt, system_prompt_content, model="gpt-4o-mini", temperature=0.7):
    """Calls the OpenAI API to generate content based on prompts.

    Args:
        client: The initialized OpenAI client.
        user_prompt: The user's input text (e.g., extracted PDF content).
        system_prompt_content: The system prompt defining the task and format.
        model (str): The OpenAI model to use.
        temperature (float): The generation temperature.

    Returns:
        The AI's response content as a string, or None if an error occurs.
    """
    if not client:
        st.error("OpenAI client not available for generation.")
        return None
    
    try:
        response = client.chat.completions.create(
            # model="gpt-4.1-nano", 
            model=model,
            messages=[
                {"role": "system", "content": system_prompt_content},
                {"role": "user", "content": user_prompt} 
            ],
            temperature=temperature,
            # max_tokens=2048 # Adjust max_tokens based on expected output length or model limits
            response_format={ "type": "json_object" } # Request JSON output directly
        )
        # output = response.choices[0].message.content.strip()
        # Since we requested JSON object, the content should already be a JSON string
        output = response.choices[0].message.content 
        return output
    except Exception as e:
        st.error(f"Error calling OpenAI API for generation: {e}")
        return None

# --- JSON Parsing Helper ---

def parse_json_response(response_text):
    """Attempts to parse a JSON object from the AI's response text.
    
    Handles potential markdown code fences (though less likely with response_format='json_object').
    
    Args:
        response_text: The raw string response from the AI.
        
    Returns:
        A dictionary parsed from JSON, or None if parsing fails.
    """
    if not response_text:
        st.error("Received empty response from API.")
        return None
        
    parsed_data = None
    error_message = None
    json_string_to_parse = response_text # Start assuming the whole thing is JSON
    
    try:
        # Minimal preprocessing: remove potential markdown fences if they still appear
        match = re.search(r'```json\n(.*?)\n```', response_text, re.DOTALL)
        if match:
            json_string_to_parse = match.group(1)
        else:
            # Optional: Trim leading/trailing whitespace that might interfere
             json_string_to_parse = response_text.strip()

        parsed_data = json.loads(json_string_to_parse)
        
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
    st.warning("Raw AI Response (attempted to parse):")
    # Use a unique key to avoid duplicate widget errors if this section appears multiple times
    st.text_area("Raw Text", json_string_to_parse, height=150, key=f"json_parsing_error_raw_{hash(json_string_to_parse)}") 
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
    
    # Determine expected JSON structure based on item_type
    if item_type == 'flashcard':
        json_structure = '{"question": "New Q", "answer": "New A"}'
        json_keys = "question, answer"
    elif item_type == 'quiz question':
        json_structure = '{"question": "New Q", "options": {"a":"OptA", "b":"OptB", "c":"OptC"}, "answer": "a"}'
        json_keys = "question, options, answer"
    else:
        st.error(f"Unknown item_type for regeneration: {item_type}")
        return None

    system_prompt = f"""You are an educational assistant improving {item_type}s.

Original Context (Excerpt): {original_text_context[:1000]}...
Original Question: {original_question}

Your task is to create a NEW and DIFFERENT {item_type} based on the provided context. The new item should cover a similar topic or concept if possible, but be distinct from the original question.

Your output MUST be a single JSON object with keys: {json_keys}.
Example: {json_structure}
Do NOT include any text outside the single JSON object.
"""
    
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini", # Use a capable but cost-effective model
            messages=[{"role": "system", "content": system_prompt}],
            max_tokens=300, # Smaller max tokens for regeneration
            temperature=0.8, # Slightly higher temp for more variation
            response_format={ "type": "json_object" }
        )
        response_text = response.choices[0].message.content # Already JSON string
        
        new_item_data = parse_json_response(response_text)
        
        # Validate structure specifically for flashcard/quiz items
        expected_keys = [key.strip() for key in json_keys.split(',')]
        if new_item_data and all(k in new_item_data for k in expected_keys):
            return new_item_data
        elif new_item_data:
             st.error(f"Regenerated {item_type} JSON missing required keys ({json_keys}).")
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
    
    # Determine expected JSON structure based on item_type
    if item_type == 'flashcard':
        json_structure = '{"question": "New Q", "answer": "New A"}'
        json_keys = "question, answer"
    elif item_type == 'quiz question':
        json_structure = '{"question": "New Q", "options": {"a":"OptA", "b":"OptB", "c":"OptC"}, "answer": "a"}'
        json_keys = "question, options, answer"
    else:
        st.error(f"Unknown item_type for addition: {item_type}")
        return None
        
    system_prompt = f"""You are an educational assistant creating {item_type}s.

Context (Excerpt): {original_text_context[:2000]}...

Existing {item_type.capitalize()} Questions (Do not repeat these exact questions or very similar ones):
{existing_q_str}

Your task is to create ONE NEW, DISTINCT {item_type} based on the provided context that is different from the existing ones.

Your output MUST be a single JSON object with keys: {json_keys}.
Example: {json_structure}
Do NOT include any text outside the single JSON object.
"""

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini", # Use a capable but cost-effective model
            messages=[{"role": "system", "content": system_prompt}],
            max_tokens=300, # Smaller max tokens for addition
            temperature=0.7,
            response_format={ "type": "json_object" }
        )
        response_text = response.choices[0].message.content # Already JSON string
        
        new_item_data = parse_json_response(response_text)
        
        # Validate structure
        expected_keys = [key.strip() for key in json_keys.split(',')]
        if new_item_data and all(k in new_item_data for k in expected_keys):
            return new_item_data
        elif new_item_data:
             st.error(f"Newly generated {item_type} JSON missing required keys ({json_keys}).")
             return None
        else:
             # parse_json_response already showed an error
             return None
             
    except Exception as e:
        st.error(f"Error during new {item_type} generation API call: {e}")
        return None 
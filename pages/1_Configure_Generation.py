import streamlit as st
import os
import re
import json # Import json module
import utils # Import the utils module

st.set_page_config(layout="centered", page_title="Configure Generation")
st.title("Configure Generation")

# --- Initialize OpenAI Client using Utility Function ---
client = utils.initialize_openai_client()
# No need to stop here, utils handles warning. Subsequent calls check client.

# --- Check if Text is Available from Upload Page ---
if not st.session_state.get("extracted_text"):
    st.warning("No text found. Please upload a PDF on the main page first.")
    if st.button("< Go to Upload"):
        st.switch_page("Akademiya.py")
    st.stop()

# --- Configuration Options UI ---
st.header("Generation Options")

st.subheader("Summary Style")
summary_style = st.radio(
    "Summary Style",
    ["Concise", "Narrative", "Analytical"],
    key="summary_style_radio",
    horizontal=True,
    label_visibility="collapsed"
)

st.subheader("Notes Style")
notes_style = st.radio(
    "Notes Style",
    ["Outline", "Sentence", "Concept Map"],
    key="notes_style_radio",
    horizontal=True,
    label_visibility="collapsed"
)

st.divider()

# Toggles with Conditional Number Input
num_flashcards_requested = 0
gen_flashcards = st.toggle("Generate Flashcards", key="gen_flashcards_toggle", value=True)
if gen_flashcards:
    # Use columns for better alignment of number input
    col_label_fc, col_input_fc = st.columns([3, 1])
    with col_label_fc:
         st.write("Number of Flashcards:") # Explicit label
    with col_input_fc:
         num_flashcards_requested = st.number_input(
             "Number of Flashcards Input", 
             min_value=1, 
             max_value=10, # Max per generation request
             value=3, 
             step=1, 
             key="num_flashcards",
             label_visibility="collapsed"
         )

num_quiz_requested = 0
gen_quiz = st.toggle("Generate Quiz", key="gen_quiz_toggle", value=True)
if gen_quiz:
    col_label_q, col_input_q = st.columns([3, 1])
    with col_label_q:
         st.write("Number of Quiz Questions:")
    with col_input_q:
         num_quiz_requested = st.number_input(
             "Number of Quiz Questions Input", 
             min_value=1, 
             max_value=10, # Max per generation request
             value=3, 
             step=1, 
             key="num_quiz",
             label_visibility="collapsed"
         )

# --- Generate Button and Logic --- 
st.divider()

if st.button("✨ Generate Content", use_container_width=True):
    extracted_text = st.session_state.get("extracted_text")
    
    if not extracted_text:
         st.error("Cannot generate, extracted text is missing from session.")
    # Also check if client initialized successfully before proceeding
    elif not client:
         st.error("Cannot generate, OpenAI client failed to initialize (check API key).", icon="🔑")
    else:
        # --- Construct the JSON-focused system prompt --- 
        prompt_sections = []
        sections_to_generate = {}

        # Build Summary instructions
        if summary_style:
            sections_to_generate["summary"] = summary_style
            style = sections_to_generate["summary"]
            # (Summary instruction logic based on style)
            if style == "Concise": summary_instruction = "Provide a concise single-paragraph summary."
            elif style == "Narrative": summary_instruction = "Provide a narrative-style summary..."
            elif style == "Analytical": summary_instruction = "Provide an analytical summary..."
            prompt_sections.append(summary_instruction)

        # Build Key Points instructions
        if notes_style:
            sections_to_generate["key_points"] = notes_style
            style = sections_to_generate["key_points"]
            # Update instruction to ask for point AND description
            notes_instruction = f"Generate 3-7 key points, each with a brief description."
            if style == "Outline": notes_instruction += " Structure them as a hierarchical outline."
            elif style == "Sentence": notes_instruction += " Write them as complete sentences."
            else: notes_instruction += " Focus on relationships between concepts."
            prompt_sections.append(notes_instruction)

        # Separate Flashcards and Quiz instructions
        if gen_flashcards and num_flashcards_requested > 0:
            sections_to_generate["flashcards"] = True
            flashcard_instruction = (
                f"Generate {num_flashcards_requested} flashcards. "
                f"Each MUST be an object with 'question' (string) and 'answer' (string)."
            )
            prompt_sections.append(flashcard_instruction)

        if gen_quiz and num_quiz_requested > 0:
            sections_to_generate["quiz"] = True
            quiz_instruction = (
                f"Generate {num_quiz_requested} multiple-choice quiz questions. "
                f"Each MUST be an object with 'question' (string), 'options' (object with string keys like 'a', 'b', 'c', etc. and string values), and 'answer' (string matching one of the option keys)."
            )
            prompt_sections.append(quiz_instruction)

        # Build JSON schema description parts
        json_schema_parts = []
        if "summary" in sections_to_generate:
            json_schema_parts.append('  "summary": "<Generated summary text>"')
        if "key_points" in sections_to_generate:
            # Update the JSON schema example for key_points
            json_schema_parts.append('''\\  "key_points": [
    { "point": "<Key Concept 1>", "description": "<Brief description 1>" }, 
    { "point": "<Key Concept 2>", "description": "<Brief description 2>" }, 
    ...
  ]''')
        if "flashcards" in sections_to_generate:
            json_schema_parts.append('''\\  "flashcards": [
    { "question": "<Q1>", "answer": "<A1>" },
    { "question": "<Q2>", "answer": "<A2>" },
    ...
  ]''')
        if "quiz" in sections_to_generate:
            json_schema_parts.append('''\\  "quiz": [
    { "question": "<Q1>", "options": {"a": "OptA", "b": "OptB", "c": "OptC"}, "answer": "a" },
    { "question": "<Q2>", "options": {"a": "OptA", "b": "OptB", "c": "OptC"}, "answer": "b" },
    ...
  ]''')

        # Combine instructions & schema for the final system prompt
        instructions_string = "\\n".join([f"- {inst}" for inst in prompt_sections])
        # Ensure proper joining for the schema string
        json_schema_string = "{\n" + ",\n".join(json_schema_parts) + "\n}" 

        system_prompt_content = f"""You are an educational assistant...
Instructions:
{instructions_string}

IMPORTANT: Output MUST be a single valid JSON object...
JSON Structure:
{json_schema_string}
"""

        st.info("Sending request to AI...")

        # --- Call API and Process Response using Utility Function --- 
        with st.spinner("Generating content with AI..."):
            # Pass the initialized client to the utility function
            gpt_response_text = utils.get_gpt_response(client, extracted_text, system_prompt_content)

            if gpt_response_text:
                st.session_state['gpt_response_raw'] = gpt_response_text 
                # Use the parsing function from utils
                parsed_data = utils.parse_json_response(gpt_response_text)
                
                st.session_state['parsing_failed'] = (parsed_data is None) # Set flag based on parser outcome
                
                # Update Session State based on parsing outcome
                if parsed_data: # Simplified check: if parser returned data
                    st.success("Content generated and parsed successfully!")
                    st.session_state['summary'] = parsed_data.get('summary')
                    st.session_state['key_points'] = parsed_data.get('key_points') 
                    # Fetch flashcards and quiz data using their respective keys
                    st.session_state['flashcards'] = parsed_data.get('flashcards') if "flashcards" in sections_to_generate else None
                    st.session_state['quiz'] = parsed_data.get('quiz') if "quiz" in sections_to_generate else None
                    
                    # Determine the list of actually generated content types
                    generated_types = []
                    if st.session_state['summary']: generated_types.append("Summary")
                    if st.session_state['key_points']: generated_types.append("Key Points")
                    if st.session_state['flashcards']: generated_types.append("Flashcards")
                    if st.session_state['quiz']: generated_types.append("Quiz") # Correct check now

                    # Store this list in session state for regeneration
                    st.session_state['content_types'] = generated_types
                else: 
                     # Error messages are now handled within parse_json_response
                     st.warning("Parsing failed. Check errors above and the raw response on the Results page.")
                     # Clear potentially bad data if parsing fails
                     st.session_state['summary'] = None
                     st.session_state['key_points'] = None
                     st.session_state['flashcards'] = None
                     st.session_state['quiz'] = None
                
                # Navigate to results page regardless of parsing success
                st.switch_page("pages/2_Results.py")
            else:
                # Handle case where API call itself failed (error shown in util func)
                st.error("Failed to get response from the AI. Check error messages above.") 
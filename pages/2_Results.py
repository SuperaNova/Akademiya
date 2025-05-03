import streamlit as st
import utils # Add utils import
# import os # Removed unused import
# Remove unused imports if OpenAI client is gone
# from openai import OpenAI 
# from dotenv import load_dotenv

st.set_page_config(layout="centered", page_title="Results")
st.title("Results")

# --- Environment Loading / Client Init (If needed for utils) ---
# Ensure client is initialized if utils.get_gpt_response needs it
client = utils.initialize_openai_client() 

# --- Retrieve Data from Session State ---
# Use .get() with default=None for safety
parsed_summary = st.session_state.get("summary")
parsed_key_points = st.session_state.get("key_points") # Expecting a list
parsed_flashcards = st.session_state.get("flashcards") # Expecting a list of dicts
parsed_quiz = st.session_state.get("quiz") # Expecting a list of dicts (same as flashcards for now)
raw_response = st.session_state.get("gpt_response_raw")
parsing_failed = st.session_state.get("parsing_failed", False)

# --- Initial Check: Ensure something was generated ---
# If nothing is available (not even raw), guide user back
if not parsed_summary and not parsed_key_points and not parsed_flashcards and not parsed_quiz and not raw_response:
    st.warning("No results found. Please generate content from the 'Configure Generation' page first.")
    if st.button("< Go to Configure"):
        st.switch_page("pages/1_Configure_Generation.py")
    st.stop()

# --- Display Generated Content ---
st.header("Generated Content")

# Display Summary
if parsed_summary:
    with st.expander("Summary", expanded=True):
        st.markdown(parsed_summary)
else:
    # Optionally indicate if summary wasn't generated/parsed
    # st.info("Summary was not generated or found.")
    pass 

# Display Key Points
if parsed_key_points:
    with st.expander("Key Points", expanded=True):
        if isinstance(parsed_key_points, list) and len(parsed_key_points) > 0:
            md_list = ""
            # Check the structure of the first item to determine format
            first_item = parsed_key_points[0]

            if isinstance(first_item, dict) and "point" in first_item and "description" in first_item:
                # Format for point and description
                st.write("Key Points (with descriptions):") # Add label for clarity
                for item in parsed_key_points:
                    point = item.get("point", "-").strip()
                    # Only add description if it exists and is not empty
                    description = item.get("description", "").strip()
                    if description:
                        md_list += f"- **{point}**: {description}\n"
                    else:
                        md_list += f"- **{point}**\n"
            elif isinstance(first_item, dict) and "point" in first_item:
                 # Format for point only (description might be missing)
                 st.write("Key Points (points only):")
                 for item in parsed_key_points:
                     point = item.get("point", "-").strip()
                     md_list += f"- **{point}**\n"
            elif isinstance(first_item, str):
                # Format for list of strings
                st.write("Key Points (simple list):")
                for point in parsed_key_points:
                    md_list += f"- {str(point).strip()}\n"
            else:
                # Fallback for unknown list structure
                st.warning("Key Points format is unexpected. Displaying raw items.")
                for item in parsed_key_points:
                    md_list += f"- {str(item)}\n" 

            st.markdown(md_list)
        
        elif isinstance(parsed_key_points, list) and len(parsed_key_points) == 0:
             st.info("No key points were generated.")
        else:
            # Handle completely unexpected format (not a list)
            st.warning("Key Points format unexpected (not a list). Displaying raw data:")
            st.markdown(str(parsed_key_points))
else:
    # Optionally indicate if key points weren't generated/parsed
    # st.info("Key Points were not generated or found.")
    pass

# --- Regeneration Section ---
st.divider()
st.subheader("Refine & Regenerate")
focus_prompt = st.text_area(
    "Optional: Guide the regeneration (e.g., 'Focus more on X', 'Summarize Y less')",
    key="regeneration_focus_prompt",
    height=100
)

if st.button("Regenerate Content", key="regenerate_button", use_container_width=True):
    # Ensure necessary data is available
    if 'extracted_text' not in st.session_state or not st.session_state['extracted_text']:
        st.error("Cannot regenerate. Original text not found in session.")
    elif 'content_types' not in st.session_state or not st.session_state['content_types']:
        st.error("Cannot regenerate. Selected content types not found in session.")
    elif not client:
         st.error("Cannot regenerate. OpenAI client not initialized.")
    else:
        with st.spinner("Regenerating content based on your focus..."):
            try:
                # Retrieve necessary info from session state
                original_text = st.session_state['extracted_text']
                selected_types = st.session_state['content_types']
                model = st.session_state.get('selected_model', utils.DEFAULT_MODEL) # Use stored or default model
                temperature = st.session_state.get('selected_temperature', utils.DEFAULT_TEMP) # Use stored or default temp

                # Construct the new prompt
                regeneration_instruction = focus_prompt.strip()
                system_prompt = utils.construct_prompt( 
                    selected_types,
                    focus_instruction=regeneration_instruction if regeneration_instruction else None
                )

                # Call the API with correct arguments
                new_response_raw = utils.get_gpt_response(
                    client, 
                    user_prompt=original_text,
                    system_prompt_content=system_prompt,
                    model=model, 
                    temperature=temperature
                )
                st.session_state['gpt_response_raw'] = new_response_raw # Store raw response again

                # Parse the new response - parse_json_response now returns None on failure
                parsed_data = utils.parse_json_response(new_response_raw)
                
                # Check if parsing succeeded (parsed_data is not None)
                if parsed_data is None:
                    st.session_state['parsing_failed'] = True
                    # Error is already shown by parse_json_response, maybe add context
                    st.error("Regeneration complete, but parsing the AI response failed.") 
                    # Clear potentially outdated parsed data
                    st.session_state['summary'] = None
                    st.session_state['key_points'] = None
                    st.session_state['flashcards'] = None
                    st.session_state['quiz'] = None
                else:
                    st.session_state['parsing_failed'] = False
                    # Update session state with new parsed data
                    st.session_state['summary'] = parsed_data.get('summary')
                    st.session_state['key_points'] = parsed_data.get('key_points')
                    st.session_state['flashcards'] = parsed_data.get('flashcards')
                    st.session_state['quiz'] = parsed_data.get('quiz')
                    st.success("Content regenerated successfully!")
                    # Rerun to immediately display the updated content
                    st.rerun() 

            except Exception as e:
                st.error(f"An error occurred during regeneration: {e}")
                st.session_state['parsing_failed'] = True # Mark as failed if API call fails

# --- Display Raw Response if Parsing Failed ---
if parsing_failed and raw_response:
    st.divider()
    st.subheader("Raw AI Response (Parsing Failed)")
    st.warning("Could not fully parse the AI response. See raw output below.")
    # Use text_area for potentially long raw output
    st.text_area("Raw Output", raw_response, height=300, disabled=True, label_visibility="collapsed")

# --- Navigation Buttons --- 
st.divider()
st.header("View Generated Assets")

col1, col2 = st.columns(2)

with col1:
    # Disable button if no flashcards are available
    flashcards_available = isinstance(parsed_flashcards, list) and len(parsed_flashcards) > 0
    if st.button("View Flashcards", use_container_width=True, disabled=not flashcards_available):
        st.switch_page("pages/3_Flashcards.py")
    elif not flashcards_available:
        st.caption("Flashcards not generated.") # Use caption for disabled state info

with col2:
    # Disable button if no quiz data is available
    quiz_available = isinstance(parsed_quiz, list) and len(parsed_quiz) > 0
    if st.button("View Quiz", use_container_width=True, disabled=not quiz_available):
        st.switch_page("pages/4_Quiz.py")
    elif not quiz_available:
        st.caption("Quiz not generated.")


#  --- Q&A Section --- 
# if client: 
#     st.divider()
#     st.header("Ask Questions About the Text")
#     if not st.session_state.get('extracted_text'):
#         ...
#     else:
#         user_question = st.text_input(...)
#         if st.button("Ask AI", ...):
#             ...
#         if st.session_state.get('qna_answer_display'):
#            ... 
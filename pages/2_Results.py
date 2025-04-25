import streamlit as st
# import os # Removed unused import
# Remove unused imports if OpenAI client is gone
# from openai import OpenAI 
# from dotenv import load_dotenv

st.set_page_config(layout="centered", page_title="Results")
st.title("Results")

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
        if isinstance(parsed_key_points, list):
            # Format list nicely
            md_list = ""
            for point in parsed_key_points:
                 point_text = str(point).strip()
                 md_list += f"- {point_text}\n" # Assume points don't have markdown bullets already
            st.markdown(md_list)
        else:
            # Handle unexpected format
            st.warning("Key Points format unexpected. Displaying raw data:")
            st.markdown(str(parsed_key_points))
else:
    # Optionally indicate if key points weren't generated/parsed
    # st.info("Key Points were not generated or found.")
    pass

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
import streamlit as st
import os
import re 
import json
import utils # Import the utils module

st.set_page_config(layout="centered", page_title="Quiz")
st.title("Generated Questions") # Match wireframe title

# --- Initialize OpenAI Client using Utility Function ---
client = utils.initialize_openai_client()

# --- Get Data from Session State ---
quiz_data = st.session_state.get("quiz") # Currently same as flashcards
original_text_context = st.session_state.get("extracted_text", "") # Get context for helpers

# --- Check if Quiz Data Exists for Display ---
if not quiz_data or not isinstance(quiz_data, list):
    st.warning("No quiz data found or format is incorrect. Please generate content first.")
    # Simplified back button
    if st.button("< Back to Configure"):
        st.switch_page("pages/1_Configure_Generation.py")
    st.stop()

# --- Add X Questions Button (Top) ---
MAX_TOTAL_QUESTIONS = 15
current_q_count = len(quiz_data) if isinstance(quiz_data, list) else 0
can_add_more_q = current_q_count < MAX_TOTAL_QUESTIONS

# --- Add New Question Section (Top) ---
if client: # Only show if client initialized
    st.subheader("Add More Questions")
    col_add_num, col_add_btn = st.columns([1, 3])
    with col_add_num:
        max_can_add_q = MAX_TOTAL_QUESTIONS - current_q_count
        num_to_add = st.number_input(
            "Add", 
            min_value=1, 
            max_value=min(10, max_can_add_q) if can_add_more_q else 1, 
            value=1, 
            step=1, 
            key="num_add", 
            label_visibility="collapsed",
            disabled=not can_add_more_q
        )
    with col_add_btn:
        if st.button(f"➕ Add {num_to_add} New Question(s)", key="add_new_q_top_x", disabled=not can_add_more_q):
            if not original_text_context:
                 st.warning("Cannot add question: Original text context missing.")
            else:
                 actual_num_to_add_q = min(num_to_add, max_can_add_q)
                 with st.spinner(f"Generating {actual_num_to_add_q} new question(s)..."):
                     new_questions_added = 0
                     for _ in range(actual_num_to_add_q):
                          # Call utility function for adding
                          new_question_data = utils.add_new_item(client, "quiz question", original_text_context, quiz_data) 
                          if new_question_data:
                               quiz_data.append(new_question_data)
                               new_questions_added += 1
                          else:
                               # Error shown in util
                               st.error("Failed to generate one of the requested questions. Stopping addition.")
                               break
                     if new_questions_added > 0:
                          st.session_state['quiz'] = quiz_data
                          st.rerun()

    if not can_add_more_q:
        st.info(f"Maximum number of questions ({MAX_TOTAL_QUESTIONS}) reached.")
    st.divider()
elif not st.session_state.get("quiz"): # Show message if quiz hasn't been generated and client isn't available
    st.info("Add/Modify features disabled. API key might be missing.")
    st.divider()

# --- Display Quiz --- 
if not quiz_data:
     st.info("No quiz questions were generated.")
else:
    st.write(f"{len(quiz_data)} question(s) available:")

    # --- Display Questions with Change Buttons (Outside Form) ---
    for i, item in enumerate(quiz_data):
        question = item.get('question', 'N/A')
        correct_answer_key = item.get('answer', '').lower()
        options = item.get('options', {})
        correct_answer_text = options.get(correct_answer_key, "N/A")
        
        col_q_display, col_btn_change = st.columns([0.9, 0.1])
        with col_q_display:
             st.markdown(f"**Q{i+1}:** {question}")
             st.caption(f"Correct Answer: {correct_answer_key.upper()}) {correct_answer_text}")
        with col_btn_change:
             if client and st.button(f"🔄", key=f"change_quiz_q_{i}", help="Change this question"):
                  if not original_text_context:
                       st.warning("Cannot change question: Original text context missing.")
                  else:
                       with st.spinner(f"Changing question {i+1}..."):
                            # Call utility function for regeneration
                            new_item_data = utils.regenerate_item(client, "quiz question", original_text_context, item)
                            if new_item_data:
                                 quiz_data[i] = new_item_data
                                 st.session_state['quiz'] = quiz_data
                                 st.rerun()
                             # Errors handled in util
        st.markdown("--- ") # Separator between question display/change and answer radio

    # --- Answer Form --- 
    with st.form(key="quiz_form"):
        st.header("Answer Questions")
        user_answers = {}
        for i, item in enumerate(quiz_data):
            # Question text is already displayed above
            # st.subheader(f"Question {i+1}: {question}") 
            options_dict = item.get('options', {})
            sorted_options = sorted(options_dict.items())
            option_labels = [f"{key.upper()}) {value}" for key, value in sorted_options]
            option_keys = [key for key, value in sorted_options]
            
            # Only show radio buttons in the form
            user_choice = st.radio(
                f"Answer for Q{i+1}:", # Add Q number for clarity
                options=option_labels,
                key=f"q_answer_{i}", # Use different key prefix
                label_visibility="visible", # Make label visible now
                index=None,
                horizontal=True # Use horizontal layout for radio
            )
            if user_choice:
                 selected_index = option_labels.index(user_choice)
                 user_answers[i] = option_keys[selected_index]
            else:
                 user_answers[i] = None
            # st.divider() # Maybe remove divider inside form for compactness

        submitted = st.form_submit_button("Submit Answers")

        # --- Results Processing --- 
        if submitted:
            score = 0
            results = []
            for i, item in enumerate(quiz_data):
                 correct_answer_key = item.get('answer', '').lower()
                 user_answer_key = user_answers.get(i)
                 is_correct = user_answer_key == correct_answer_key
                 if is_correct:
                      score += 1
                 results.append({
                     "question": item.get('question', 'N/A'), # Include Q text in results
                     "user_answer": user_answer_key.upper() if user_answer_key else "Not Answered",
                     "correct_answer": correct_answer_key.upper(),
                     "is_correct": is_correct
                 })
            
            # Display results below the form
            st.divider()
            st.header("Quiz Results")
            st.metric("Your Score", f"{score}/{len(quiz_data)}")
            st.divider()
            for res in results:
                 st.markdown(f"**Q:** {res['question']}")
                 if res['is_correct']:
                      st.success(f"➡️ Your answer: {res['user_answer']} (Correct)")
                 else:
                      st.error(f"➡️ Your answer: {res['user_answer']} (Incorrect - Correct was {res['correct_answer']})")
                 st.markdown("&nbsp;") # Add small space

# --- Back Button --- 
st.divider()
if st.button("< Back to Results"):
    st.switch_page("pages/2_Results.py")

# TODO: Implement interactive quiz interface (e.g., show questions, options, check answers)
# TODO: Potentially adjust prompt in Configure page to generate distinct quiz questions if needed 
import streamlit as st
import os
import re
import json
import utils # Import the utils module

st.set_page_config(layout="centered", page_title="Flashcards")
st.title("Generated Cards")

# --- Initialize OpenAI Client using Utility Function ---
client = utils.initialize_openai_client()

# --- Get Data from Session State ---
flashcards = st.session_state.get("flashcards")
original_text_context = st.session_state.get("extracted_text", "")

MAX_TOTAL_CARDS = 15
current_card_count = len(flashcards) if isinstance(flashcards, list) else 0
can_add_more = current_card_count < MAX_TOTAL_CARDS

# --- Add New Card Section ---
if client: # Only show if client initialized successfully
    st.subheader("Add More Cards")
    col_add_num, col_add_btn = st.columns([1, 3])
    
    with col_add_num:
        max_can_add = MAX_TOTAL_CARDS - current_card_count
        num_to_add_fc = st.number_input(
            "Add Cards Input", 
            min_value=1, 
            max_value=min(10, max_can_add) if can_add_more else 1, 
            value=1, step=1, key="num_add_fc", 
            label_visibility="collapsed",
            disabled=not can_add_more
        ) 
    with col_add_btn:
        if st.button(f"➕ Add {num_to_add_fc} New Card(s)", key="add_new_fc_top_x", disabled=not can_add_more):
            if not original_text_context:
                  st.warning("Cannot add card: Original text context missing.")
            else:
                 actual_num_to_add = min(num_to_add_fc, max_can_add)
                 with st.spinner(f"Generating {actual_num_to_add} new card(s)..."):
                     new_cards_added = 0
                     for _ in range(actual_num_to_add):
                         # Call utility function for adding
                         new_card_data = utils.add_new_item(client, "flashcard", original_text_context, flashcards)
                         if new_card_data:
                              flashcards.append(new_card_data)
                              new_cards_added += 1
                         else:
                              # Error message shown in util func
                              st.error("Failed to generate one of the requested cards. Stopping addition.")
                              break # Stop trying if one fails
                     if new_cards_added > 0:
                          st.session_state['flashcards'] = flashcards
                          st.rerun()

    if not can_add_more:
         st.info(f"Maximum number of cards ({MAX_TOTAL_CARDS}) reached.")
    st.divider()
elif not st.session_state.get("flashcards"): # Show message if cards haven't been generated yet and client isn't available
    st.info("Add/Modify features disabled. API key might be missing.")
    st.divider()

# --- Check if Flashcards Exist for Display ---
if not flashcards or not isinstance(flashcards, list):
    st.warning("No flashcards found or format is incorrect. Please generate content first.")
    # Back button logic
    if st.button("< Back to Configure"):
        st.switch_page("pages/1_Configure_Generation.py")
    st.stop()

# --- Display Flashcards --- 
st.header(f"Generated Flashcards ({len(flashcards)}/{MAX_TOTAL_CARDS})")
st.divider()

if not flashcards:
     st.info("No flashcards were generated or found in session state.")
else:
    # Display each card
    for i, card in enumerate(flashcards):
        question = card.get('question', 'N/A')
        answer_text = card.get('answer', 'Answer not found')

        expander_title = f"**Card {i+1}:** {question}"

        with st.expander(expander_title):
            st.markdown(f"**Answer:** {answer_text}")
            st.divider()

            # Regeneration button INSIDE the expander
            regen_button_key = f"change_q_{i}" 
            # Use the initialized client object here
            if client and st.button("🔄 Change This Question", key=regen_button_key, help="Ask AI for a different question on this topic"):
                with st.spinner("Asking for a new question..."):
                    # Call utility function for regeneration
                    new_card_data = utils.regenerate_item(client, "flashcard", original_text_context, card)
                    if new_card_data:
                         flashcards[i] = new_card_data
                         st.session_state["flashcards"] = flashcards
                         st.rerun()
                     # Error messages handled within utils.regenerate_item

        st.markdown("<br>", unsafe_allow_html=True) # Spacer between cards

# --- Navigation --- 
st.divider()
if st.button("< Back to Results"):
    st.switch_page("pages/2_Results.py")

# TODO: Implement interactive flashcard display (e.g., one card at a time with reveal answer button) 
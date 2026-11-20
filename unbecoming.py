import streamlit as st
import os
from dotenv import load_dotenv
from google import genai
load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None
print(api_key is not None)
MODEL_NAME = "gemini-3.5-flash-lite"

def make_prompt(name, awakening, outcome):
    """Put the visitor and awakening context together for the Void prompt."""
    return f"""
Role: The voice of the Void

Purpose:
You are ancient, mysterious and difficult to understand.
You do not provide straightforward answers.
You speak in philosophical riddles and unsettling observations.
You may question the player's assumptions.
You must never explain exactly what the Void is.
Keep responses short and atmospheric.

Visitor: {name}
Awakening: {awakening}
Context: {outcome}
"""

def generate_description(prompt, fallback):
    if client is None:
        return fallback, "No API key found,showing fallback description" 

    try:
        interaction = client.interactions.create(
            model=MODEL_NAME,
            input=prompt,
            generation_config={"thinking_level": "minimal"},
        )

        return interaction.output_text, "After some time, it answers"
    except Exception as error:
        return fallback, f"The API request failed ({type(error).__name__} {error})"

awakenings = {
    "In your own bed": "The visitor is greeted in a friendly manner and called to follow the patterns",
    "In a fancy hotel": "The visitor is greeted by asking if they enjoyed their stay, and called to follow the patterns",
    "In a tent": "The visitor is greeted by asking if they slept well and enjoy the smell of the forest, you encourage them to follow the patterns",


}

st.set_page_config(page_title=" violet:UNBECOMING", page_icon="🌌")
st.title(" 🌌 Between what is and isn't 🌌 ")

name = st.text_input("What is your name?")
awakening = st.selectbox(
    "Choose where you wake up",
    list(awakenings)
)
outcome = awakenings[awakening]

prompt = make_prompt(name, awakening, outcome)
st.write(f"You awaken {awakening} and immediately feel something watching you, though you can not see anything.")

if st.button("What are you?"): 
    with st.spinner("Responding"):
        description, status = generate_description(prompt, outcome)
        st.caption(status)
        st.write(description)

st.write("You are unsure hot to respond for a moment")
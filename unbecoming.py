import os

import streamlit as st
from dotenv import load_dotenv
from google import genai

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None
MODEL_NAME = "gemini-3.5-flash-lite"

awakenings = {
    "In your own bed": "The visitor is greeted in a friendly manner and called to follow the patterns. Give them a pair of scissors, tell them they will come in handy, but don't say what for.",
    "In a fancy hotel": "The visitor is greeted by asking if they enjoyed their stay, and called to follow the patterns. Give them a pair of scissors, tell them they will come in handy, but don't say what for",
    "In a tent": "The visitor is greeted by asking if they slept well and enjoy the smell of the forest, you encourage them to follow the patterns. Give them a pair of scissors, tell them they will come in handy, but don't say what for",
}


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
        return fallback, "No API key found, showing fallback description"

    try:
        interaction = client.interactions.create(
            model=MODEL_NAME,
            input=prompt,
            generation_config={"thinking_level": "minimal"},
        )
        return interaction.output_text, "After some time, it answers"
    except Exception as error:
        return fallback, f"The API request failed ({type(error).__name__} {error})"


def take_damage(amount):
    st.session_state.health = max(0, st.session_state.health - amount)


def heal_player(amount):
    old_essence = st.session_state.essence
    st.session_state.essence = min(
        st.session_state.max_essence,
        st.session_state.essence + amount,
    )
    return st.session_state.essence - old_essence


def show_room(title, description):
    st.subheader(title)
    st.write(description)


def show_enemy(name, description):
    show_room(name, description)


def generate_story(room, outcome, action, fallback_message):
    if client is None:
        st.warning("No API key found, using fallback")
        return fallback_message

    inventory_text = ", ".join(st.session_state.inventory)
    prompt = f"""
Player: {st.session_state.player_name}
Room: {room}
Health: {st.session_state.health}/{st.session_state.max_health}
Inventory: {inventory_text}

Action: {action}
Outcome: {outcome}

Role: The voice of the Void

Purpose:
You are ancient, mysterious and difficult to understand.
You do not provide straightforward answers.
You speak in philosophical riddles and unsettling observations.
You may question the player's assumptions.
You must never explain exactly what the Void is.
Keep responses short and atmospheric.
"""
    try:
        interaction = client.interactions.create(
            model=MODEL_NAME,
            input=prompt,
            generation_config={"thinking_level": "minimal"},
        )
        if interaction.output_text:
            return interaction.output_text
        st.warning("Returned empty text")
        return fallback_message
    except Exception as error:
        st.error(f"Error: {error}")
        return fallback_message


def show_continue_button():
    if st.button("Continue"):
        st.session_state.action_complete = False


def set_result(kind, text):
    st.session_state.action_complete = True
    st.session_state.result_kind = kind
    st.session_state.result_text = text


def show_result():
    kind = st.session_state.result_kind
    value = st.session_state.result_text

    if kind == "pass":
        st.success(f"You pass with flying colours, {st.session_state.name}, + Essence points.")
    elif kind == "lose":
        st.error(f"💔 OH NO: You have lost {value} Essence.")
    elif kind == "success":
        st.success("✅ Success! You can pass through to the next part of the story")
        if value:
            st.write(value)
    else:
        st.info("The journey continues...")
        if value:
            st.write(value)


def awakening():
    name = st.text_input("What is your name?")
    st.session_state.name = name or "Initiate"

    location = st.selectbox("Choose where you wake up", list(awakenings))
    outcome = awakenings[location]

    prompt = make_prompt(st.session_state.name, location, outcome)
    st.write(
        f"You awaken {location} and immediately feel something watching you, "
        "though you cannot see anything."
    )

    if st.button("What are you?"):
        with st.spinner("Responding"):
            description, status = generate_description(prompt, outcome)
            st.caption(status)
            st.write(description)
            st.write(" :blue[You have no idea why, but the disembodied voice has given you a pair of scissors]")
    elif st.button("You pause"):
        st.write("You are unsure how to respond for a moment")
        show_continue_button()


st.set_page_config(page_title=" DTSN", page_icon="🌌")
st.title("🌌 Dance the spiral, neverending 🌌")
st.subheader("Between what is and isn't")

defaults = {
    "essence": 100,
    "max_essence": 100,
    "inventory": ["Scissors"],
    "action_complete": False,
    "game_started": False,
    "result_kind": "story",
    "result_text": "",
}


def shifting_room():
    enemy = st.radio(
        "Look for the patterns, listen and watch carefully. Where would you like to go first?",
        ["Sphinx", "The Chapel", "The Mountain"],
    )

    if enemy == "Sphinx":
        show_enemy("Sphinx", "A giant Sphinx lashes her tail and studies you.")
        if not st.session_state.action_complete:
            left, right = st.columns(2)
            with left:
                if st.button("Ask the Sphinx a question"):
                    story = generate_story(
                        room="Sphinx",
                        outcome="You solve the riddles and can move forwards",
                        action="Solve riddles",
                        fallback_message="You displease the Sphinx and are not allowed past",
                    )
                    set_result("success", story)
                    st.rerun()
            with right:
                if st.button("🏃 Run past"):
                    story = generate_story(
                        room="Sphinx",
                        outcome="The player answers the riddle correctly",
                        action="pressing the correct button",
                        fallback_message="You solve the Sphinxes riddle and it seems pleased with you",
                    )
                    set_result("success", story)
                    st.rerun()
        else:
            show_result()
            show_continue_button()

def chamber_of_chance():
    

awakening()



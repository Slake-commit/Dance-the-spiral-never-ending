import os
import random
import streamlit as st
from dotenv import load_dotenv
from google import genai

load_dotenv()
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None
MODEL_NAME = "gemini-3.5-flash-lite" 

# ---------------------------------------------------------------- setup
st.set_page_config(page_title="Unbecoming", page_icon="🌌")

VOID_VOICE = """
Role: The voice of the Void

Purpose:
You are ancient, mysterious and difficult to understand.
You do not provide straightforward answers.
You speak in philosophical riddles and unsettling observations.
You may question the player's assumptions.
You must never explain exactly what the Void is.
Keep responses short and atmospheric.
"""

SCISSORS_LINE = (
    "Give them a pair of scissors, you are not allowed to say what they are for but you can say they will be useful"
)

awakenings = {
    "In your own bed": f"The visitor is greeted in a friendly manner and called to follow the patterns. {SCISSORS_LINE}",
    "In a fancy hotel": f"The visitor is greeted by asking if they enjoyed their stay, and called to follow the patterns. {SCISSORS_LINE}",
    "In a tent": f"The visitor is greeted by asking if they slept well and enjoy the smell of the forest, and encouraged to follow the patterns. {SCISSORS_LINE}",
}

defaults = {
    "name": "Initiate",
    "essence": 50,
    "max_essence": 100,
    "inventory": ["Scissors"],
    "action_complete": False,
    "game_started": False,
    "void_reply": "",
    "result_kind": "story",
    "result_text": "",
    "result_amount": 0,
    "cleared": [],
    "chapel_found": 0,
    "clues": [],
}
for key, value in defaults.items():
    st.session_state.setdefault(key, value)


# ---------------------------------------------------------------- AI helpers
def call_void(prompt, fallback):
    """Ask the model; return (text, ok). Falls back gracefully."""
    if client is None:
        return fallback, False
    try:
        interaction = client.interactions.create(
            model=MODEL_NAME,
            input=prompt,
            generation_config={"thinking_level": "minimal"},
        )
        if interaction.output_text:
            return interaction.output_text, True
        return fallback, False
    except Exception as error:
        st.error(f"The API request failed ({type(error).__name__}: {error})")
        return fallback, False


def make_prompt(name, awakening, outcome):
    return f"""{VOID_VOICE}
Visitor: {name}
Awakening: {awakening}
Context: {outcome}
"""


def generate_story(room, outcome, action, fallback_message):
    prompt = f"""
Player: {st.session_state.name}
Room: {room}
Essence: {st.session_state.essence}/{st.session_state.max_essence}
Inventory: {", ".join(st.session_state.inventory)}

Action: {action}
Outcome: {outcome}
{VOID_VOICE}"""
    text, _ = call_void(prompt, fallback_message)
    return text


#Game stuff
def lose_essence(amount):
    st.session_state.essence = max(0, st.session_state.essence - 10)


def gain_essence(amount):
    old = st.session_state.essence
    st.session_state.essence = min(
        st.session_state.max_essence, old + 5
    )
    return st.session_state.essence - old


def set_result(kind, text, amount=0):
    st.session_state.action_complete = True
    st.session_state.result_kind = kind
    st.session_state.result_text = text
    st.session_state.result_amount = amount


def _continue():
    st.session_state.action_complete = False


def show_continue_button():
    st.button("Continue", on_click=_continue)


def show_result():
    kind = st.session_state.result_kind
    text = st.session_state.result_text
    amount = st.session_state.result_amount

    if kind == "pass":
        st.success(f"You pass with flying colours, {st.session_state.name}.")
    elif kind == "lose":
        st.error(f"💔 OH NO: You have lost {amount} Essence.")
    elif kind == "heal":
        st.success(f"✨ You regain {amount} Essence.")
    elif kind == "success":
        st.success("✅ Success! You can pass through to the next part of the story.")
    else:
        st.info("The journey continues...")
    if text:
        st.write(text)


def show_room(title, description):
    st.subheader(title)
    st.write(description)


def scene_intro(scene, description, prompt):
    seen_scenes = st.session_state.setdefault("scene_intros", [])
    if scene not in seen_scenes:
        st.write(description)
        st.caption(prompt)
        seen_scenes.append(scene)


#Acts/scenes
def awakening():
    st.session_state.name = st.text_input("What is your name?") or "Initiate"

    location = st.selectbox("Choose where you wake up", list(awakenings))
    outcome = awakenings[location]

    st.write(
        f"You awaken {location.lower()} and immediately feel something "
        "watching you, though you cannot see anything."
    )

    if st.button("What are you?"):
        with st.spinner("Responding..."):
            prompt = make_prompt(st.session_state.name, location, outcome)
            text, ok = call_void(prompt, outcome)
            st.session_state.void_reply = text
            if not ok:
                st.caption("No answer from the Void, showing fallback.")

    if st.session_state.void_reply:
        st.write(st.session_state.void_reply)
        st.write(
            ":blue[You have no idea why, but the disembodied voice has "
            "given you a pair of scissors.]"
        )

        if st.button("Follow the patterns"):
         st.session_state.game_started = True
         st.rerun()


def sphinx_room():
    show_room("Sphinx", "A giant Sphinx lashes her tail and studies you.")
    st.write(
        f"'Answer my riddles, {st.session_state.name}, and you may pass'"
    )
    st.write(" :blue[You wonder how she knows your name]")
    RIDDLES = [
    {"q": "'I speak without a mouth and hear without ears. What am I?'",
     "options": ["An echo", "A shadow", "A dream"], "answer": "An echo"},
    {"q": "'The more of me you take, the more you leave behind.'",
     "options": ["Footsteps", "Time", "Memories"], "answer": "Footsteps"},
    {"q": "'What has keys but opens no locks?'",
     "options": ["A piano", "A map", "A cage"], "answer": "A piano"},
]

    if "riddle" not in st.session_state:
        riddle = random.choice(RIDDLES)
        st.session_state.riddle = riddle
        st.session_state.riddle_options = random.sample(
            riddle["options"], len(riddle["options"])
        )

    riddle = st.session_state.riddle
    st.write(f"*{riddle['q']}*")

    for option in st.session_state.riddle_options:
        if st.button(option, key=f"riddle_{option}"):
            if option == riddle["answer"]:
                gain_essence(5)
                story = generate_story(
                    "Sphinx", "The player answers correctly and may pass",
                    f"Answered '{option}'", "The Sphinx purrs and looks impressed. The way is open.",
                )
                set_result("success", story)
            else:
                lose_essence(10)
                story = generate_story(
                    "Sphinx", "The player answers wrongly and loses essence",
                    f"Answered '{option}'", "The Sphinx smiles. That was not it.",
                )
                set_result("lose", story, 10)
            del st.session_state.riddle
            st.rerun()


def chapel_room():
    show_room("The Chapel", "Candles flicker. The Keeper greets you with open arms. He seems genuine and kind")
    keeper_clues = [
        "The offering bowls are empty by dawn, yet the Keeper's robes grow finer.",
        "Today's sermon contradicts yesterday's, word for word.",
        "Behind the altar, you peek... And see the coins the Keeper has been keeping for himself",
    ]
    scene_intro(
        "chapel",
        "A chapel led by a charming Keeper who is a little too generous",
        "Everyone here is smiling... But something makes you suspicious.",
    )

    if "chapel" in st.session_state.cleared:
        st.write("The chapel is quiet now. The candles burn lower, and more honest.")
        return

    found = st.session_state.chapel_found
    for clue in keeper_clues[:found]:
        st.write(f"🔎 {clue}")

    if st.button("Accept his blessing"):
        lose_essence(10)
        set_result("lose", "He thanks you warmly. The blessing feels like a debt.", 10)
        st.rerun()

    if found < len(keeper_clues) and st.button("Look around"):
        st.session_state.chapel_found += 1
        st.rerun()

    if st.button("Confront the Keeper"):
        if found >= 2:
            st.session_state.cleared.append("chapel")
            st.session_state.clues.append("The Keeper's ledger")
            set_result("success", "His smile slips. The congregation sees it too. "
                       "The ledger falls from his sleeve.")
        else:
            lose_essence(10)
            set_result("lose", "He talks circles around you. Without proof, "
                       "you are the one who looks foolish.", 10)
        st.rerun()



def mountain_room():
    show_room(
        "The Mountain",
        "It rises, though you never see it move. A narrow path disappears into the clouds.",
    )
    st.write("The wind carries a sound like your own voice calling from above.")
    climb, search = st.columns(2)

    with climb:
        if st.button("Take a rest"):
                gain_essence(5)
            
                story = generate_story(
                    "The Mountain",
                    "The player decides to rest and watch nature, this helps them to focus clearly",
                    "Resting on the mountain lets them see a new perspective",
                    "Explain clearly that the mountain shows you that waiting, watching, and taking things slowly can often be the most beneficial path",
                )
                set_result("success", story)

        elif st.button("Fight upwards"):
                lose_essence(10)
                story = generate_story(
                        "The Mountain",
                        "The player keeps climbing and loses essence",
                        "Climbing the mountain causes exhaustion",
                        "The path shifts beneath you. Something inside you remains behind.",
                    )
                set_result("lose", story, 10)


def shifting_room():
    if st.session_state.action_complete:
        show_result()
        show_continue_button()
        return

    place = st.radio(
        "Look for the patterns, listen and watch carefully. Where would you like to go first?",
        ["Sphinx", "The Chapel", "The Mountain"],
    )
    if place == "Sphinx":
        sphinx_room()
    elif place == "The Chapel":
        chapel_room()
    else:
        mountain_room()


#Beginning
st.title("🌌 Unbecoming 🌌")
st.subheader("Dance the spiral, never ending")

if not st.session_state.game_started:
    awakening()
else:
    st.progress(
        st.session_state.essence / st.session_state.max_essence,
        text=f"Essence: {st.session_state.essence}/{st.session_state.max_essence}",
    )
    if st.session_state.essence <= 0:
        st.error("You come undone. The spiral keeps turning without you.")
        if st.button("Begin again"):
            for k, v in defaults.items():
                st.session_state[k] = v
            st.rerun()
    else:
        shifting_room()

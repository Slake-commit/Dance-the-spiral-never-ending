import copy
import os
import random
import streamlit as st
from dotenv import load_dotenv
from google import genai

load_dotenv()
api_key = st.secrets["GEMINI_API_KEY"]
client = genai.Client(api_key=api_key) if api_key else None
MODEL_NAME = "gemini-3.5-flash-lite"

#setup
st.set_page_config(page_title="Ever Becoming", page_icon="🌌")

VOID_VOICE = """
Role: The voice of the Void

Purpose:
You are ancient, mysterious and difficult to understand.
You do not provide straightforward answers.
You speak in philosophical riddles and unsettling observations.
You may question the player's assumptions.
You must never explain exactly what the Void is.
Keep responses short and atmospheric.
Do not insult or demean the player.
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
    "sphinx_cleared": False,
    "mountain_done": False,
    "hard_riddle_open": False,
    "chapel_found": 0,
    "clues": ["The chapel Ledger"],
    "watched": False,
    "chamber_step": 0,
    "stage": "shifting",  # shifting -> chamber -> whispering
}
for key, value in defaults.items():
    # deepcopy so the lists in `defaults` are never mutated by the game
    st.session_state.setdefault(key, copy.deepcopy(value))


def reset_game():
    for k, v in defaults.items():
        st.session_state[k] = copy.deepcopy(v)
    for k in ("scene_intros", "riddle", "riddle_options"):
        st.session_state.pop(k, None)


# AI
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


# game 
def lose_essence(amount):
    st.session_state.essence = max(0, st.session_state.essence - amount)


def gain_essence(amount):
    old = st.session_state.essence
    st.session_state.essence = min(
        st.session_state.max_essence,
        st.session_state.essence + amount,
    )
    return st.session_state.essence - old


def set_result(kind, text, amount=0):
    st.session_state.action_complete = True
    st.session_state.result_kind = kind
    st.session_state.result_text = text
    st.session_state.result_amount = amount


def shifting_room_complete():
    return (
        st.session_state.sphinx_cleared
        and "chapel" in st.session_state.cleared
        and st.session_state.mountain_done
    )


def _continue():
    st.session_state.action_complete = False
    # Move on to the Chamber only after the player has read the last result
    if st.session_state.stage == "shifting" and shifting_room_complete():
        st.session_state.stage = "chamber"


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
        if amount:
            st.success(f"✨ You regain {amount} Essence.")
        else:
            st.success("✨ Your essence is already full.")
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


# Act 1: Awakening
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


# Act 2: Shifting Room
RIDDLES = [
    {"q": "'I speak without a mouth and hear without ears. What am I?'",
     "options": ["An echo", "A shadow", "A dream"], "answer": "An echo"},
    {"q": "'The more of me you take, the more you leave behind.'",
     "options": ["Footsteps", "Time", "Memories"], "answer": "Footsteps"},
    {"q": "'What has keys but opens no locks?'",
     "options": ["A piano", "A map", "A cage"], "answer": "A piano"},
]


def sphinx_room():
    if st.session_state.sphinx_cleared:
        st.write("The Sphinx lowers her head. You have already passed.")
        return

    show_room("Sphinx", "A giant Sphinx lashes her tail and studies you.")
    st.write(f"'Answer my riddles, {st.session_state.name}, and you may pass'")
    st.write(":blue[You wonder how she knows your name]")

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
                    f"Answered '{option}'",
                    "The Sphinx purrs and looks impressed. The way is open.",
                )
                set_result("success", story)
                st.session_state.sphinx_cleared = True
            else:
                lose_essence(10)
                story = generate_story(
                    "Sphinx", "The player answers wrongly and loses essence",
                    f"Answered '{option}'",
                    "The Sphinx smiles. That was not it.",
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
                       "The ledger falls from his sleeve. For some reason you feel the need to keep the ledger, so you pocket it")
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

    if st.session_state.mountain_done:
        st.write("The mountain has nothing more to teach you today. It never hurries.")
        return

    rest, climb = st.columns(2)

    with rest:
        if st.button("Take a rest"):
            gain_essence(5)
            story = generate_story(
                "The Mountain",
                "The player decides to rest and watch nature, which helps them focus clearly",
                "Resting on the mountain lets them see a new perspective",
                "You sit, and the mountain shows you that waiting, watching and going slowly "
                "is often the most useful path.",
            )
            st.session_state.mountain_done = True
            set_result("success", story)
            st.rerun()
    

    with climb:
        # Fighting upwards still lets you pass, but it costs essence
        if st.button("Fight upwards"):
            lose_essence(10)
            story = generate_story(
                "The Mountain",
                "The player keeps climbing and loses essence",
                "Climbing the mountain causes exhaustion",
                "The path shifts beneath you. Something inside you remains behind.",
            )
            st.session_state.mountain_done = True
            set_result("lose", story, 10)
            st.rerun()


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


# Act 3: Chamber of Chance
BAND_EFFECT = {
    "crisis": -12,
    "rough": -5,
    "steady": 3,
    "graceful": 8,
}


def band_for(raw, adjusted):
    if adjusted <= 5:
        return "crisis"
    if adjusted <= 10:
        return "rough"
    if adjusted <= 15:
        return "steady"
    return "graceful"


SCENARIOS = [
    {"title": "The River",
     "intro": "A river runs through the chamber, and it is never where you left it.",
     "hint": "You watch. The water pulls left, then right, then left. A breath, a rhythm.",
     "clue": "The river does not hurry, yet it arrives.",
     "crisis": "You rush the water and the water laughs. It carries you farther than you meant to go.",
     "rough": "You are carried, not carrying. You reach the far bank with less of yourself.",
     "steady": "You step where the current rests, and the river lets you cross.",
     "graceful": "You stop resisting and are carried exactly where you needed to go."},

    {"title": "The Stranger",
     "intro": "A doorway appears that was not there a moment ago. A stranger leans against it, smiling with great patience. 'There is a quicker way,' he says. 'Trust me.'",
     "hint": "You ask questions and listen to how he answers, not only to what he says.",
     "clue": "Ask not whether the guide is kind, but where the road leads.",
     "crisis": "You were careful, and it does not matter. The shortcut was a circle. You arrive where you began, lighter.",
     "rough": "He was half honest. The path exists, but the toll was never mentioned.",
     "steady": "He is neither saint nor snake. The shortcut holds, and it costs you only a little.",
     "graceful": "He tells the truth, and it seems to surprise him as much as you. At the end he nods like an old friend, though you have never met."},

    {"title": "The Lantern",
     "intro": "A lantern hangs in the dark, and it hums. Not the name you gave, but an older one. Its glow is warm and slow, and you cannot look away. It seems so close. Only a few steps, surely.",
     "hint": "You watch it, and you notice: it is never farther than a few steps. Only ever a few steps.",
     "clue": "The point has already moved. Walk anyway.",
     "crisis": "You run. It rises a little further each time, and you run harder. When you stop, breathless, it is exactly a few steps ahead still, humming, patient. You have never been so tired of something so beautiful.",
     "rough": "You reach where it was. It is a little ahead. You reach that, and it is a little ahead again. You curse, you laugh, you curse again. Somewhere along the way you drop something of yourself.",
     "steady": "You reach where it was. It is a little ahead. You sigh, and walk on, less angry than the last time.",
     "graceful": "You reach where it was. It is a little ahead. You laugh. The walking has become a joy as your laughter echoes in the dark whilst you follow the lantern you can never catch, and the lantern glows warmer... as if it was waiting for you to notice this the entire time."},
]


def chamber_room():
    st.write(f"You move onto the next level, this is The Chamber of Chance. Careful, {st.session_state.name}, even the most talented initiates can lose it all to Lady Luck")
    if st.session_state.action_complete:
        show_result()
        show_continue_button()
        return

    step = st.session_state.chamber_step
    if step >= len(SCENARIOS):
        st.write("The Chamber falls silent. Nothing here is finished. Nothing ever is.")
        if st.button("Go on"):
            st.session_state.stage = "whispering"
            st.rerun()
        return

    sc = SCENARIOS[step]
    show_room(sc["title"], sc["intro"])

    if st.session_state.watched:
        st.caption(sc["hint"])
    elif st.button("Watch and wait"):
        st.session_state.watched = True
        st.rerun()

    if st.button("Roll the die"):
        raw = random.randint(1, 20)
        bonus = 2 if st.session_state.watched else 0
        band = band_for(raw, min(20, raw + bonus))
        effect = BAND_EFFECT[band]
        note = f"🎲 {raw}" + (" (+2 from watching)" if bonus else "")
        text = f"{note}\n\n{sc[band]}"

        if effect < 0:
            lose_essence(-effect)
            set_result("lose", text, -effect)
        else:
            gained = gain_essence(effect)
            if band == "graceful" and sc["clue"] not in st.session_state.clues:
                st.session_state.clues.append(sc["clue"])
            set_result("heal", text, gained)

        st.session_state.chamber_step += 1
        st.session_state.watched = False
        st.rerun()


# Act 4: Whispering Room (to be worked on)
def whispering_room():
    LEDGER = "The chapel Ledger"
    show_room(
        "The Whispering Room",
        "The Void is closer here. It has been listening all along.",
    )

    if "ledger_given" not in st.session_state:
        st.session_state.ledger_given = False

    if st.session_state.ledger_given == False:
        st.write("The walls don't echo here. They answer.")
        st.write("*You carried something here. Show me.*")

        if LEDGER in st.session_state.clues:
            if st.button("Hand over the ledger"):
                st.session_state.ledger_given = True
                st.rerun()
        else:
            st.write("You carry nothing the Void recognises.")

        if st.button("Leave without offering anything"):
            lose_essence(5)
            st.session_state.stage = "final"
            st.rerun()

    elif st.session_state.ledger_given:
        st.write("The Void turns the ledger over, slowly. Names. Sums. Signatures.")
        st.write("*You saw who they really were. Good.*")
        st.write("*Now hear this: do not trust me blindly either. Not me, not them, not anyone who asks you to stop looking.*")

        if st.button("Go to the Final Threshold"):
            st.session_state.stage = "final"
            st.rerun()
    else: 
        final_threshold()

def final_threshold():
    show_room(
        "The Final Threshold",
        "The Void counts what is left of you.",
    )

    if "web_cut" not in st.session_state:
        st.session_state.web_cut = False

    essence = st.session_state.essence
    st.write(f"Essence remaining: {essence}")

    if essence > 60:
        st.write("*You have learned. I am impressed, and I don't say that often.*")
        st.write("*Keep going. The spiral never ends, and neither does your growth.*")
    elif essence >= 45:
        st.write("*You have passed. But little has changed.*")
        st.write("*You are much as you were when you arrived. That is not a failure. It is a place to begin.*")
    else:
        st.write("*You have passed. But only just.*")
        st.write("*Look more. Think more. The answers were closer than you thought.*")

    st.divider()

    if st.session_state.web_cut == False:
        st.write("Threads close around you, soft and sticky. A web, pale and endless, holds you where you stand.")
        st.write("In your hand, the scissors you were gifted.")

        if st.button("Cut through the web"):
            st.session_state.web_cut = True
            st.rerun()

    else:
        st.write("Snip. The threads fall away. Snip. The world tears open like paper.")
        st.write("You wake where you first chose. The air is quiet and ordinary. It was only a dream, you think.")
        st.write("Then you feel something cold beside you. The scissors.")

        if st.button("Begin again"):
            st.session_state.clear()
            st.rerun()


# Beginning 
st.title("🌌 Ever Becoming 🌌")
st.subheader("Dance the spiral, never ending")
st.write("ESSENCE: Essence is what sustains you. Stack it and carry it with you through the thresholds. "
         "Each loss weakens your ability to persevere. "
         "Gather what you can. Question what you are told. Protect what you have learned. "
         "You cannot become without first having something to become from."
st.sidebar.title("Inventory")

if len(st.session_state.inventory) == 0:
    st.sidebar.write("Empty for now.")
else:
    for item in st.session_state.inventory:
        st.sidebar.write("- " + item)

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
            reset_game()
            st.rerun()
    elif st.session_state.stage == "shifting":
        shifting_room()
    elif st.session_state.stage == "chamber":
        chamber_room()
    elif st.session_state.stage == "whispering":
        whispering_room()
    elif st.session_state.stage == "final":
        final_threshold()


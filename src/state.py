import json
import os

STATE_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "state.json")


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    return {"posted_ids": [], "affiliate_index": 0, "last_run": None}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


import os
import random
import uuid
from typing import Dict

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

app = FastAPI(title="Wordle API Server")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

WORD_BANK = [
    "APPLE", "TRAIN", "HOUSE", "PLANT", "SMART", "WORLD",
    "LIGHT", "BRAIN", "CLOUD", "WATER",
    "ABOUT", "ABOVE", "ACTOR", "ACUTE", "ADMIT", "ADOPT",
    "ADULT", "AFTER", "AGAIN", "AGENT", "AGREE", "AHEAD",
    "ALARM", "ALBUM", "ALERT", "ALIEN", "ALIKE", "ALIVE",
    "ALLOW", "ALONE", "ALONG", "ALTER", "AMONG", "ANGER",
    "ANGLE", "ANGRY", "APART", "APPLY", "ARGUE", "ARISE",
    "ARRAY", "ARROW", "ASIDE", "ASSET", "AUDIO", "AUDIT",
    "AVOID", "AWAKE", "AWARE", "BADGE", "BAKER", "BASIC",
    "BASIS", "BEACH", "BEGIN", "BEING", "BELOW", "BENCH",
    "BLACK", "BLAME", "BLANK", "BLAST", "BLEED", "BLEND",
    "BLOCK", "BLOOD", "BOARD", "BOAST", "BONUS", "BOOST",
    "BOUND", "BREAD", "BREAK", "BRICK", "BRIEF", "BRING",
    "BROAD", "BROWN", "BRUSH", "BUILD", "BUNCH", "BUYER",
    "CABLE", "CANDY", "CARGO", "CARRY", "CATCH", "CAUSE",
    "CHAIN", "CHAIR", "CHALK", "CHARM", "CHART", "CHASE",
    "CHEAP", "CHECK", "CHEST", "CHIEF", "CHILD", "CHOSE",
    "CIVIL", "CLAIM", "CLASS", "CLEAN", "CLEAR", "CLIMB",
    "CLOCK", "CLOSE", "COACH", "COAST", "COUNT", "COURT",
    "COVER", "CRASH", "CREAM", "CRIME", "CROSS", "CROWD",
    "CROWN", "CURVE", "CYCLE", "DAILY", "DANCE", "DEATH",
    "DELAY", "DEPTH", "DRAFT", "DRAMA", "DREAM", "DRIVE",
    "EAGLE", "EARLY", "EARTH", "EIGHT", "EMPTY", "ENEMY",
    "ENJOY", "ENTER", "EQUAL", "ERROR", "EVENT", "EVERY",
    "EXACT", "EXIST", "FAITH", "FALSE", "FAULT", "FIELD",
    "FIGHT", "FINAL", "FIRST", "FLAME", "FLASH", "FLOAT",
    "FLOOR", "FLOUR", "FLUID", "FOCUS", "FORCE", "FORTH",
    "FORTY", "FORUM", "FRAME", "FRESH", "FRONT", "FRUIT",
    "GIANT", "GLASS", "GLOBE", "GRACE", "GRADE", "GRAND",
    "GRANT", "GRASS", "GREAT", "GREEN", "GROUP", "GUARD",
    "GUESS", "GUIDE", "HAPPY", "HEART", "HEAVY", "HOTEL",
    "HUMAN", "IMAGE", "INDEX", "INPUT", "ISSUE", "JUDGE",
    "KNIFE", "LAYER", "LEMON", "LEVEL", "LIMIT", "LUNCH",
    "MAGIC", "MAJOR", "MARCH", "MATCH", "MEDAL", "MONEY",
    "MONTH", "MUSIC", "NIGHT", "NOVEL", "NURSE", "OCEAN",
    "OFFER", "ORDER"
]

MAX_ATTEMPTS = 6

games_db: Dict[str, dict] = {}

stats = {
    "total_games": 0,
    "wins": 0
}


class NewGameRequest(BaseModel):
    hard_mode: bool = False


class GuessRequest(BaseModel):
    game_id: str
    guess: str


def calculate_feedback(guess, target):
    feedback = ["absent"] * 5
    remaining = {}

    for char in target:
        remaining[char] = remaining.get(char, 0) + 1

    for i in range(5):
        if guess[i] == target[i]:
            feedback[i] = "correct"
            remaining[guess[i]] -= 1

    for i in range(5):
        if feedback[i] != "correct":
            if remaining.get(guess[i], 0) > 0:
                feedback[i] = "present"
                remaining[guess[i]] -= 1

    return feedback


# Create new game
@app.post("/api/new-game")
def start_new_game(req: NewGameRequest = NewGameRequest()):

    game_id = str(uuid.uuid4())
    target_word = random.choice(WORD_BANK)

    games_db[game_id] = {
        "target": target_word,
        "status": "PLAYING",
        "attempts": 0,
        "hard_mode": req.hard_mode,
        "green_hints": {}
    }

    stats["total_games"] += 1

    return {
        "game_id": game_id,
        "hard_mode": req.hard_mode,
        "message": "New game started!"
    }


@app.post("/api/guess")
def process_guess(req: GuessRequest):

    game_id = req.game_id
    guess = req.guess.strip().upper()

    if game_id not in games_db:
        raise HTTPException(
            status_code=404,
            detail="Game session not found."
        )

    game = games_db[game_id]

    if game["status"] != "PLAYING":
        raise HTTPException(
            status_code=400,
            detail="Game has already ended."
        )

    if len(guess) != 5 or not guess.isalpha():
        raise HTTPException(
            status_code=400,
            detail="Word must be 5 letters."
        )

    if guess not in WORD_BANK:
        raise HTTPException(
            status_code=400,
            detail="Not in word list!"
        )

    if game["hard_mode"]:
        for position, letter in game["green_hints"].items():

            if guess[position] != letter:
                raise HTTPException(
                    status_code=400,
                    detail="Hard Mode: Must use revealed hint at green position."
                )

    target = game["target"]

    feedback = calculate_feedback(guess, target)

    game["attempts"] += 1

    for i, result in enumerate(feedback):
        if result == "correct":
            game["green_hints"][i] = guess[i]

    is_correct = (guess == target)

    if is_correct:
        game["status"] = "WON"
        stats["wins"] += 1

    elif game["attempts"] >= MAX_ATTEMPTS:
        game["status"] = "LOST"

    game_over = game["status"] in ["WON", "LOST"]

    return {
        "guess": guess,
        "feedback": feedback,
        "is_correct": is_correct,
        "attempts": game["attempts"],
        "game_over": game_over,

        "target_word": target if game_over else None
    }


@app.get("/api/stats")
def get_stats():

    total = stats["total_games"]
    wins = stats["wins"]

    win_rate = 0

    if total > 0:
        win_rate = (wins / total) * 100

    return {
        "total_games": total,
        "wins": wins,
        "win_rate": round(win_rate, 1)
    }


if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", "8000"))

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port
    )

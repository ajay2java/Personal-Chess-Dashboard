
import json
import os
import sys
import time
from pathlib import Path

import requests

API_URL = "https://lichess.org/api/games/user/{username}"
DATA_DIR = Path("data/raw")
STATE_FILE = DATA_DIR / "lichess_state.json"


def load_last_timestamp(username: str) -> int | None:
    """Return the createdAt (ms) of the newest game already saved, if any."""
    if not STATE_FILE.exists():
        return None
    state = json.loads(STATE_FILE.read_text())
    return state.get(username.lower())


def save_last_timestamp(username: str, timestamp_ms: int) -> None:
    state = json.loads(STATE_FILE.read_text()) if STATE_FILE.exists() else {}
    state[username.lower()] = timestamp_ms
    STATE_FILE.write_text(json.dumps(state, indent=2))


def fetch_games(username: str, since_ms: int | None):
    """Stream games from the Lichess API, yielding one dict per game."""
    params = {
        "clocks": "true",      # clock time after every move -> time-per-move chart
        "evals": "true",       # engine evals, for games that were analyzed on Lichess
        "opening": "true",     # ECO code + opening name
        "pgnInJson": "true",   # keep the full PGN too, handy for python-chess later
        "finished": "true",    # skip games still in progress
        "sort": "dateAsc",     # oldest first, so the state file always moves forward
    }
    if since_ms is not None:
        params["since"] = since_ms + 1  # +1 so we don't re-fetch the last saved game

    headers = {"Accept": "application/x-ndjson"}  # one JSON object per line
    token = os.environ.get("LICHESS_TOKEN")
    if token:
        headers["Authorization"] = f"Bearer {token}"

    while True:
        with requests.get(
            API_URL.format(username=username),
            params=params,
            headers=headers,
            stream=True,
            timeout=60,
        ) as resp:
            if resp.status_code == 429:
                # Lichess asks clients to wait a full minute after a rate limit.
                print("Rate limited. Waiting 60 seconds...")
                time.sleep(60)
                continue
            resp.raise_for_status()

            for line in resp.iter_lines():
                if line:  # the stream can include blank keep-alive lines
                    yield json.loads(line)
            return


def main() -> None:
    if len(sys.argv) != 2:
        sys.exit("Usage: python lichess.py YOUR_USERNAME")
    username = sys.argv[1]

    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out_path = DATA_DIR / f"lichess_{username.lower()}.ndjson"

    since_ms = load_last_timestamp(username)
    print(f"Fetching games for {username}"
          + (f" newer than {since_ms}" if since_ms else " (full history)"))

    count = 0
    newest_ms = since_ms
    with out_path.open("a", encoding="utf-8") as f:
        for game in fetch_games(username, since_ms):
            f.write(json.dumps(game) + "\n")
            count += 1
            newest_ms = max(newest_ms or 0, game["createdAt"])
            if count % 100 == 0:
                print(f"  {count} games saved...")
                f.flush()
                save_last_timestamp(username, newest_ms)  # checkpoint progress

    if newest_ms is not None:
        save_last_timestamp(username, newest_ms)
    print(f"Done. {count} new games written to {out_path}")


if __name__ == "__main__":
    main()

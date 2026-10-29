# ChessLens (A Personal Chess Dashboard)

SQL analysis of my Lichess games, stored in PostgreSQL.
DONE: Wrote SQL queries to answer relevant questions related to the online games I play.
GOAL: To create my own dashboard in Streamlit to use analytics to inform my chess improvement.

## Setup

1. Create `.env` and fill in your Postgres password.
2. Run:

```
pip install -r requirements.txt
python ingest/lichess.py [ENTER LICHESS USERNAME]      # download games -> data/raw/
python ingest/load_lichess.py        # load into the "chess" Postgres database
```

Re-run the last two commands any time to pick up new games.

## Tables

- `raw.lichess_games`: each game exactly as the Lichess API returned it (JSONB)
- `core.games`: one row per game, from my perspective
- `core.moves`: one row per half-move, with clock and engine eval

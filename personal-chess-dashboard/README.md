# Chess Dashboard

SQL analysis of my Lichess games, stored in PostgreSQL.

## Setup

1. Copy `.env.example` to `.env` and fill in your Postgres password.
2. Run:

```
pip install -r requirements.txt
python ingest/lichess.py KingAJ      # download games -> data/raw/
python ingest/load_lichess.py        # load into the "chess" Postgres database
```

Re-run the last two commands any time to pick up new games.

## Tables

- `raw.lichess_games`: each game exactly as the Lichess API returned it (JSONB)
- `core.games`: one row per game, from my perspective
- `core.moves`: one row per half-move, with clock and engine eval

Column definitions: `sql/schema/01_create_tables.sql`

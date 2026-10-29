
import json
import os
from datetime import datetime, timezone
from pathlib import Path

import psycopg
from psycopg import sql

USERNAME = "KingAJ"
ROOT = Path(__file__).resolve().parent.parent
RAW_FILE = ROOT / "data" / "raw" / f"lichess_{USERNAME.lower()}.ndjson"
ENV_FILE = ROOT / ".env"
SCHEMA_FILE = ROOT / "sql" / "schema" / "01_create_tables.sql"


def load_settings() -> dict:
    """Read connection settings from .env (KEY=value lines), with sensible defaults."""
    settings = {
        "PGHOST": "localhost",
        "PGPORT": "5432",
        "PGUSER": "postgres",
        "PGPASSWORD": "",
        "PGDATABASE": "chess",
    }
    if ENV_FILE.exists():
        for line in ENV_FILE.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, value = line.split("=", 1)
                settings[key.strip()] = value.strip()
    # Real environment variables win over the file (handy in Codespaces).
    for key in settings:
        settings[key] = os.environ.get(key, settings[key])
    return settings


def connect(settings: dict, dbname: str) -> psycopg.Connection:
    return psycopg.connect(
        host=settings["PGHOST"],
        port=settings["PGPORT"],
        user=settings["PGUSER"],
        password=settings["PGPASSWORD"],
        dbname=dbname,
    )


def ensure_database(settings: dict) -> None:
    """Create the target database if it doesn't exist yet."""
    target = settings["PGDATABASE"]
    with connect(settings, "postgres") as admin:
        admin.autocommit = True  # CREATE DATABASE can't run inside a transaction
        exists = admin.execute("SELECT 1 FROM pg_database WHERE datname = %s", [target]).fetchone()
        if not exists:
            admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(target)))
            print(f"Created database '{target}'.")


def ms_to_ts(ms):
    """Lichess timestamps are milliseconds since 1970 (UTC)."""
    if ms is None:
        return None
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).replace(tzinfo=None)


def find_my_color(game: dict) -> str | None:
    """Return 'white' or 'black' depending on which side you played."""
    for color in ("white", "black"):
        user = game.get("players", {}).get(color, {}).get("user", {})
        if user.get("id", "").lower() == USERNAME.lower():
            return color
    return None


def game_result(game: dict, my_color: str) -> str:
    """Translate Lichess's 'winner' field into win/loss/draw from your side."""
    if game.get("status") in ("aborted", "noStart"):
        return "aborted"
    winner = game.get("winner")
    if winner is None:
        return "draw"
    return "win" if winner == my_color else "loss"


def parse_game(game: dict) -> tuple | None:
    """Flatten one raw game into a row for core.games."""
    my_color = find_my_color(game)
    if my_color is None:
        return None  # not your game (shouldn't happen, but be safe)
    opp_color = "black" if my_color == "white" else "white"
    me = game["players"][my_color]
    opp = game["players"][opp_color]
    clock = game.get("clock") or {}
    opening = game.get("opening") or {}
    sans = (game.get("moves") or "").split()

    return (
        game["id"],
        "lichess",
        ms_to_ts(game.get("createdAt")),
        ms_to_ts(game.get("lastMoveAt")),
        game.get("rated"),
        game.get("variant"),
        game.get("speed"),
        clock.get("initial"),
        clock.get("increment"),
        my_color,
        game_result(game, my_color),
        game.get("status"),
        me.get("rating"),
        me.get("ratingDiff"),
        opp.get("user", {}).get("name", "anonymous/AI"),
        opp.get("rating"),
        opening.get("eco"),
        opening.get("name"),
        len(sans),
        "analysis" in game,
    )


def parse_moves(game: dict) -> list[tuple]:
    """Flatten one raw game into rows for core.moves (one per ply)."""
    my_color = find_my_color(game)
    if my_color is None:
        return []
    sans = (game.get("moves") or "").split()
    clocks = game.get("clocks") or []        # centiseconds left after each ply
    analysis = game.get("analysis") or []    # engine info for each ply, if analyzed

    rows = []
    for i, san in enumerate(sans):
        ply = i + 1
        color = "white" if ply % 2 == 1 else "black"
        info = analysis[i] if i < len(analysis) else {}
        judgment = (info.get("judgment") or {}).get("name")
        rows.append((
            game["id"],
            ply,
            (ply + 1) // 2,
            color,
            color == my_color,
            san,
            clocks[i] if i < len(clocks) else None,
            info.get("eval"),
            info.get("mate"),
            judgment,
        ))
    return rows


def load_raw(conn) -> int:
    """Copy new games from the NDJSON file into raw.lichess_games."""
    if not RAW_FILE.exists():
        raise SystemExit(f"No raw file at {RAW_FILE}. Run: python ingest/lichess.py {USERNAME}")

    rows = []
    with RAW_FILE.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                game = json.loads(line)
                rows.append((game["id"], line))

    with conn.cursor() as cur:
        # Stage everything in a temporary table, then insert only games we don't have yet.
        cur.execute("CREATE TEMP TABLE staging (game_id VARCHAR, payload JSONB) ON COMMIT DROP")
        with cur.copy("COPY staging (game_id, payload) FROM STDIN") as copy:
            for row in rows:
                copy.write_row(row)
        cur.execute("""
            INSERT INTO raw.lichess_games (game_id, payload)
            SELECT DISTINCT ON (game_id) game_id, payload FROM staging
            ON CONFLICT (game_id) DO NOTHING
        """)
        return cur.rowcount


def rebuild_core(conn) -> None:
    """Rebuild core.games and core.moves from everything in the raw table.

    Rebuilding from scratch each time keeps things simple: if you fix a bug
    in the parsing code, just re-run and the core tables are corrected.
    """
    with conn.cursor() as cur:
        # psycopg turns JSONB into Python dicts automatically.
        raw_games = [p for (p,) in cur.execute("SELECT payload FROM raw.lichess_games")]

        game_rows, move_rows = [], []
        for g in raw_games:
            row = parse_game(g)
            if row:
                game_rows.append(row)
                move_rows.extend(parse_moves(g))

        cur.execute("TRUNCATE core.moves, core.games")
        # COPY is Postgres's fast bulk-load path: far quicker than row-by-row INSERTs.
        with cur.copy("COPY core.games FROM STDIN") as copy:
            for row in game_rows:
                copy.write_row(row)
        with cur.copy("COPY core.moves FROM STDIN") as copy:
            for row in move_rows:
                copy.write_row(row)


def main() -> None:
    settings = load_settings()
    ensure_database(settings)

    # Everything below runs in one transaction: it all succeeds or nothing changes.
    with connect(settings, settings["PGDATABASE"]) as conn:
        conn.execute(SCHEMA_FILE.read_text())
        new = load_raw(conn)
        rebuild_core(conn)
        n_games = conn.execute("SELECT count(*) FROM core.games").fetchone()[0]
        n_moves = conn.execute("SELECT count(*) FROM core.moves").fetchone()[0]

    print(f"Loaded {new} new raw games.")
    print(f"core.games: {n_games} rows | core.moves: {n_moves} rows")
    print(f"Database: {settings['PGDATABASE']} on {settings['PGHOST']}:{settings['PGPORT']}")


if __name__ == "__main__":
    main()

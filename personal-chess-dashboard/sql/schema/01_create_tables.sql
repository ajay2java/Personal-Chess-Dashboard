-- Schema for the chess dashboard (PostgreSQL).
-- Three layers: raw (API output as-is), core (clean tables), analytics (your views).

CREATE SCHEMA IF NOT EXISTS raw;
CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS analytics;

-- One row per game, exactly as the Lichess API returned it.
CREATE TABLE IF NOT EXISTS raw.lichess_games (
    game_id    VARCHAR PRIMARY KEY,
    payload    JSONB NOT NULL,
    loaded_at  TIMESTAMP NOT NULL DEFAULT current_timestamp
);

-- One row per game, from YOUR perspective.
CREATE TABLE IF NOT EXISTS core.games (
    game_id          VARCHAR PRIMARY KEY,
    platform         VARCHAR NOT NULL,      -- 'lichess' (chess.com later)
    played_at        TIMESTAMP NOT NULL,    -- game start, UTC
    ended_at         TIMESTAMP,             -- last move, UTC
    rated            BOOLEAN,
    variant          VARCHAR,               -- 'standard', 'chess960', ...
    time_class       VARCHAR,               -- 'bullet', 'blitz', 'rapid', 'classical', 'correspondence'
    clock_initial_s  INTEGER,               -- base time in seconds
    clock_increment_s INTEGER,              -- increment in seconds
    my_color         VARCHAR NOT NULL,      -- 'white' or 'black'
    result           VARCHAR NOT NULL,      -- 'win', 'loss', 'draw', 'aborted'
    end_reason       VARCHAR,               -- 'mate', 'resign', 'outoftime', 'draw', 'stalemate', ...
    my_rating        INTEGER,
    my_rating_diff   INTEGER,               -- rating points gained/lost from this game
    opponent         VARCHAR,
    opp_rating       INTEGER,
    eco              VARCHAR,               -- e.g. 'B20'
    opening_name     VARCHAR,               -- e.g. 'Sicilian Defense: Bowdler Attack'
    num_plies        INTEGER,               -- half-moves played
    has_eval         BOOLEAN                -- true if the game has engine analysis
);

-- One row per half-move (ply).
CREATE TABLE IF NOT EXISTS core.moves (
    game_id      VARCHAR NOT NULL,
    ply          INTEGER NOT NULL,          -- 1 = White's first move, 2 = Black's first move, ...
    move_number  INTEGER NOT NULL,          -- the number shown on the board (1, 1, 2, 2, ...)
    color        VARCHAR NOT NULL,          -- side that made this move
    is_my_move   BOOLEAN NOT NULL,
    san          VARCHAR NOT NULL,          -- move in algebraic notation, e.g. 'Nf3'
    clock_cs     INTEGER,                   -- clock remaining AFTER this move, centiseconds
    eval_cp      INTEGER,                   -- engine eval after this move, centipawns, White's perspective
    eval_mate    INTEGER,                   -- mate-in-N instead of cp (positive = White mates)
    judgment     VARCHAR,                   -- Lichess label: 'Inaccuracy', 'Mistake', 'Blunder'
    PRIMARY KEY (game_id, ply)
);




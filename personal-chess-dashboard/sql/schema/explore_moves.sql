SELECT * FROM core.moves;

SELECT move_number, color, clock_cs FROM core.moves WHERE is_my_move = true;

WITH lagged_moves AS (
    SELECT 
        *,
        LAG(clock_cs) OVER (PARTITION BY game_id ORDER BY move_number) AS prev_clock
    FROM core.moves
    WHERE color = 'white'
)
SELECT 
    game_id,
    move_number,
    clock_cs,
    CASE 
        WHEN move_number = 1 OR prev_clock IS NULL THEN 0
        ELSE GREATEST(0, prev_clock - clock_cs)
    END AS time_spent
FROM lagged_moves;
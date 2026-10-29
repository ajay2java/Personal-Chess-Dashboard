   SELECT current_database() AS db,
          (SELECT count(*) FROM core.games) AS games,
          (SELECT count(*) FROM core.moves) AS moves;

SELECT * FROM raw.lichess_games;
SELECT * FROM core.games;
SELECT * FROM core.moves;

---Clean Dates
SELECT
    played_at::date AS date_played,
    CURRENT_DATE - played_at::date AS days_since_played
FROM core.games;

--- list of piece color, opening, result, and rating change by # of days since game was played
SELECT my_color, opening_name, result, my_rating_diff FROM core.games WHERE time_class = 'blitz' AND (CURRENT_DATE - played_at::date) <= 31;

---number of games by color

SELECT my_color, COUNT(*) FROM core.games WHERE time_class = 'blitz' AND (CURRENT_DATE - played_at::date) <= 31 GROUP BY my_color;

---how many games with white (plus w/d/l record) over 'x' number of days

SELECT result, COUNT(*) FROM core.games WHERE my_color = 'white' AND (CURRENT_DATE - played_at::date) <= 31 GROUP BY result;

---how many games with black (plus w/d/l record) over 'x' number of days

SELECT result, COUNT(*) FROM core.games WHERE my_color = 'black' AND (CURRENT_DATE - played_at::date) <= 31 GROUP BY result;

---rating gained/lost

SELECT SUM(my_rating_diff) AS Rating_Change FROM core.games WHERE time_class = 'blitz' AND (CURRENT_DATE - played_at::date) <= 31;

---White Opening Quantity
SELECT opening_name, COUNT(*) FROM core.games WHERE my_color = 'white' AND (CURRENT_DATE - played_at::date) <= 31 GROUP BY opening_name ORDER BY COUNT(*) DESC;

---Black Opening Quantity
SELECT opening_name, COUNT(*) FROM core.games WHERE my_color = 'black' AND (CURRENT_DATE - played_at::date) <= 31 GROUP BY opening_name ORDER BY COUNT(*) DESC;

---White Opening Performance (w/d/l)
SELECT
    opening_name,
    COUNT(*) FILTER (WHERE result = 'win') AS win,
    COUNT(*) FILTER (WHERE result = 'draw') AS draw,
    COUNT(*) FILTER (WHERE result = 'loss') AS loss
FROM core.games 
WHERE my_color = 'white' 
    AND (CURRENT_DATE - played_at::date) <= 31 
GROUP BY opening_name;

---Black Opening Performance (w/d/l)
SELECT
    opening_name,
    COUNT(*) FILTER (WHERE result = 'win') AS win,
    COUNT(*) FILTER (WHERE result = 'draw') AS draw,
    COUNT(*) FILTER (WHERE result = 'loss') AS loss
FROM core.games 
WHERE my_color = 'black' 
    AND (CURRENT_DATE - played_at::date) <= 31 
GROUP BY opening_name;

---Average Opponent Rating
SELECT ROUND(AVG(opp_rating)) AS opponent_rating_avg FROM core.games WHERE (CURRENT_DATE - played_at::date) <= 31;

----------------------------------------------------------------------------------------------------------------------------------------------------------------------------
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------

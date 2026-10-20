# Courtline runbook (NBA, started Oct 20 2026)

Steven's NBA model, built the same way as Gridline (NFL) but kept separate: its own folder (`courtline/` in this project), its own pages and its own bankroll. Plan: odds history first, then a player minutes and props model, then totals; sides last, if ever. Paper-trade 4 to 6 weeks against closing lines before any real money.

## Data (checked Oct 20 2026)

- The cloud workspace cannot reach stats.nba.com, cdn.nba.com or basketball-reference.com (egress refused).
- hoopR-nba-data (sportsdataverse, ESPN-sourced) is reachable with git: `git clone --depth 1 --filter=blob:none --no-checkout https://github.com/sportsdataverse/hoopR-nba-data`, then `git sparse-checkout set --no-cone 'nba/team_box/parquet/*' 'nba/player_box/parquet/*' 'nba/schedules/parquet/*' 'nba/betting_lines/*'` and `git checkout`. The GitHub API and release downloads are not available to this session; the data lives in the repo itself.
- Files (season = the year the season ends, so 2027 = 2026-27): `nba/team_box/parquet/team_box_YYYY.parquet`, `nba/player_box/parquet/player_box_YYYY.parquet` (2002+), `nba/schedules/parquet/nba_schedule_YYYY.parquet` (2027 has the full 2026-27 schedule, Oct 20 2026 to Apr 11 2027), `nba/pbp`, `nba/officials`, `nba/game_rosters`.
- Historical lines: `nba/betting_lines/closing_lines_odds_api.parquet` (Odds API consensus closing spread and total, keyed by ESPN game_id, Jul 2020 to Jun 2026, 7,942 games) and `games-archive.json` (2017 to 2023). No historical player prop lines anywhere, so props can only be graded against results until we save our own prop odds.

## Odds going forward

Steven's PC already pulls NFL odds (see gridline/ODDS.md). NBA spreads, totals and moneylines (sport key `basketball_nba`) cost about 3 credits a pull; one pull a day before the evening slate is about 90 credits a month, which fits the free tier (500) next to the NFL's ~105. Player props use the per-event endpoint and cost credits per game per market, so they need a paid tier to pull nightly. To do: add an NBA pull to fetch_odds.py on the PC writing to `odds/snapshots/nba_odds_<stamp>.json` in the repo.

## Backtest v0 (backtest_v0.py, Oct 20 2026)

Team form model (EWMA offensive and defensive rating and pace from ESPN box scores, half life 12 games, 30% regression between seasons; rest days and back-to-backs), on top of the closing line, walk forward with 2022 to 2026 seasons as test (6,573 games):
- Vegas average miss: margin 10.55, total 14.22. The model matched it exactly (10.56, 14.22): it adds nothing.
- Spread leans: 0.5+ point 252-244 (50.8%); the model almost never moves the line 1+ point.
- Total leans: 1+ 863-803 (51.8%), 1.5+ 356-361 (49.7%), 2+ 121-128 (48.6%). No edge.
- Back-to-backs vs the closing line: home team on a back-to-back -0.65 pts vs the spread (978 games); away team on a back-to-back: total +1.23 over the closing total (1,158 games, about 2.3 standard errors; worth re-testing, not proven).
- Conclusion: as expected, NBA closing sides and totals are not beatable with team form. Next is the player minutes and props model.

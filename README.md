# Courtline: an NBA model tested against the betting market

**Project page:** https://stevopotpie.github.io/courtline/

Courtline is the NBA companion to [Gridline](https://github.com/stevopotpie/gridline), my NFL model. Same idea: build projections from public data, test them on games the model has not seen against the closing line, and only trust what holds up.

## Status (November 2026)

- **Data:** team and player box scores, schedules and closing spreads and totals (2020 to 2026, about 7,900 games) from [hoopR-nba-data](https://github.com/sportsdataverse/hoopR-nba-data).
- **Odds history:** a daily pull from The Odds API (spreads, totals, moneylines across US books), saved as snapshots for closing line value.
- **Backtest v0:** a team form model (offensive and defensive rating, pace, rest, back-to-backs) on top of the closing line, walk forward over 2021-22 to 2025-26 (6,573 games). It matched Vegas exactly and found no edge on sides or totals, which is what you would expect from NBA closing lines. One thing worth re-testing: games where the road team is on a back-to-back finished 1.2 points over the closing total (1,158 games).
- **Next:** a player minutes and props model, where an NBA edge is most plausible.
- **Paper trading:** every 2026-27 projection is logged in `data/predictions.csv` and graded in public on the site against the line from the last odds pull before tip, for at least 4 to 6 weeks before any real money.

## The site

[stevopotpie.github.io/courtline](https://stevopotpie.github.io/courtline/) rebuilds itself twice a day on GitHub Actions: after the evening odds pull, and at midday once last night's box scores land.

- **[Predictions](https://stevopotpie.github.io/courtline/predictions.html)**: the next three days of games with the market's consensus line, Courtline's projection and side, plus every graded game this season
- **[In-game](https://stevopotpie.github.io/courtline/in-game.html)**: live scores from ESPN every 30 seconds, Courtline's live win chance for each team, and a check for any live moneyline you type in
- **[Research](https://stevopotpie.github.io/courtline/research.html)**: the backtest against the close, back to backs, home court by season and current team ratings
- **[Calculator](https://stevopotpie.github.io/courtline/calculator.html)**: any two teams, any rest, any line
- **[Bet log](https://stevopotpie.github.io/courtline/bet-log.html)**: log bets and see Courtline's chance against the price, saved in your own browser only

Every 2026-27 projection is out of sample: the live model is trained only on earlier seasons, and each game is graded against the consensus line from the last odds pull before tip.

## Files

- `model.py`: team form ratings, the walk forward backtest, live projections and the graded season log (`python3 -I model.py HOOPR_DIR .`)
- `live_train.py`: trains the in-game win model on hoopR play by play (2020 to 2026) and saves `data/live_model.json`; rerun after each season
- `site/build.py`, `site/ingame.py`, `site/courtline.css`, `site/courtline.js`: build the pages in `docs/` from `data/courtline.json`
- `run_site.sh`: fetch hoopR data, run the model, build the site (what the workflows run)
- `data/predictions.csv`: every projection this season, with the line, Courtline's number and the final
- `backtest_v0.py`: the original team form backtest (`python3 -I backtest_v0.py PATH_TO_hoopR-nba-data`)
- `actions/` and `.github/workflows/`: the daily odds pull and site rebuilds
- `pc/`: the original Windows odds pull
- `paper_trades.csv`: the first hand-logged projections
- `RUNBOOK.md`: data sources, findings and how each run works

Projections are research, not betting advice. Sports betting is not legal in every state. If gambling stops being fun, call or text 1-800-GAMBLER.

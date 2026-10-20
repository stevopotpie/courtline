# Courtline: an NBA model tested against the betting market

Courtline is the NBA companion to [Gridline](https://github.com/stevopotpie/gridline), my NFL model. Same idea: build projections from public data, test them on games the model has not seen against the closing line, and only trust what holds up.

## Status (October 2026)

- **Data:** team and player box scores, schedules and closing spreads and totals (2020 to 2026, about 7,900 games) from [hoopR-nba-data](https://github.com/sportsdataverse/hoopR-nba-data).
- **Odds history:** a daily pull from The Odds API (spreads, totals, moneylines across US books), saved as snapshots for closing line value.
- **Backtest v0:** a team form model (offensive and defensive rating, pace, rest, back-to-backs) on top of the closing line, walk forward over 2021-22 to 2025-26 (6,573 games). It matched Vegas exactly and found no edge on sides or totals, which is what you would expect from NBA closing lines. One thing worth re-testing: games where the road team is on a back-to-back finished 1.2 points over the closing total (1,158 games).
- **Next:** a player minutes and props model, where an NBA edge is most plausible.
- **Paper trading:** every projection is logged in `paper_trades.csv` and graded against results and closing lines for 4 to 6 weeks before any real money.

## Files

- `backtest_v0.py`: the team form backtest (`python3 -I backtest_v0.py PATH_TO_hoopR-nba-data`)
- `pc/`: the Windows odds pull (`fetch_nba_odds.py`, run and schedule scripts)
- `paper_trades.csv`: logged projections and results
- `RUNBOOK.md`: data sources, findings and how each run works

Research, not betting advice. Sports betting is not legal in every state.

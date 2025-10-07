# pages/2_Team_Stats.py
import streamlit as st
import pandas as pd

from courtvision.data.nba_client import (
    list_all_teams, recent_seasons,
    get_team_basic_stats, get_team_roster, get_team_players_season_stats,
)

st.title("Team Stats")

# Controls
c1, c2, c3 = st.columns([2,1,1])
teams = list_all_teams()
team_name = c1.selectbox("Team", options=[t["full_name"] for t in teams])
season = c2.selectbox("Season", options=recent_seasons(10))
refresh = c3.button("Refresh from API")

team = next(t for t in teams if t["full_name"] == team_name)
team_id = team["team_id"]

# Header phrase
st.markdown(f"## {team_name} **Stats** {season}")

# Dashboard
with st.spinner("Loading team dashboard…"):
    dash = get_team_basic_stats(team_id, season, refresh=refresh)

if dash.empty:
    st.error("Could not load team dashboard for that season.")
    st.stop()

def _g(col, default=None):
    # be resilient to naming differences
    for c in (col, col.upper(), col.title(), col.replace("_"," ").title()):
        if c in dash.columns: return dash[c].iloc[0]
    return default

W = int(_g("W", 0) or 0); L = int(_g("L", 0) or 0); W_PCT = float(_g("W_PCT", 0.0) or 0.0)
PTS = float(_g("PTS", 0.0) or 0.0); REB = float(_g("REB", 0.0) or 0.0); AST = float(_g("AST", 0.0) or 0.0)
OFF_RTG = float(_g("OFF_RATING", 0.0) or 0.0); DEF_RTG = float(_g("DEF_RATING", 0.0) or 0.0); PACE = float(_g("PACE", 0.0) or 0.0)

k1,k2,k3,k4 = st.columns(4)
k1.metric("Record", f"{W}-{L}", f"{W_PCT*100:.1f}%")
k2.metric("PTS/G", f"{PTS:.1f}")
k3.metric("REB/G", f"{REB:.1f}")
k4.metric("AST/G", f"{AST:.1f}")

k5,k6,k7 = st.columns(3)
k5.metric("Off Rating", f"{OFF_RTG:.1f}")
k6.metric("Def Rating", f"{DEF_RTG:.1f}")
k7.metric("Pace", f"{PACE:.1f}")

st.markdown("### Team Leaders & Player Stats")

# Player per-game stats
with st.spinner("Loading player season stats…"):
    pstats = get_team_players_season_stats(team_id, season, refresh=refresh)

if pstats.empty:
    roster = get_team_roster(team_id, season, refresh=refresh)
    if not roster.empty:
        st.caption("Season player averages unavailable; showing roster instead.")
        st.dataframe(roster, use_container_width=True)
    else:
        st.info("No player data available for this season.")
    st.stop()

# Normalize column names
rename = {
    "PLAYER_NAME": "Name",
    "GP": "GP", "MIN": "MIN", "PTS": "PTS", "REB": "REB", "AST": "AST",
    "STL": "STL", "BLK": "BLK", "TOV": "TO", "PF": "PF",
    "FG3_PCT": "3P%", "FT_PCT": "FT%",
}
for old, new in rename.items():
    if old in pstats.columns and new not in pstats.columns:
        pstats = pstats.rename(columns={old:new})

# Convert percent decimals to %
for pct_col in ["3P%", "FT%"]:
    if pct_col in pstats.columns:
        pstats[pct_col] = (pstats[pct_col].astype(float) * 100).round(1)

# AST/TO
if "AST" in pstats.columns and "TO" in pstats.columns:
    pstats["AST/TO"] = pstats.apply(
        lambda r: (float(r["AST"]) / float(r["TO"])) if float(r["TO"]) != 0 else None, axis=1
    )
    pstats["AST/TO"] = pstats["AST/TO"].round(2)

# Leaders (text only)
def _leader(col):
    if col not in pstats.columns: return None
    row = pstats.sort_values(col, ascending=False).head(1)
    return row.iloc[0]["Name"], float(row.iloc[0][col])

leaders = {"Points": _leader("PTS"), "Rebounds": _leader("REB"), "Assists": _leader("AST")}
lc = st.columns(3)
for (label, item), col in zip(leaders.items(), lc):
    if item:
        name, val = item
        col.markdown(f"**{label}**")
        col.subheader(f"{val:.1f}")
        col.caption(name)
    else:
        col.write("—")

# Display table (sorted by PTS)
cols = ["Name","GP","MIN","PPG","RPG","APG","SPG","BPG","3P%","FT%","AST/TO"]
show = [c for c in cols if c in pstats.columns]
disp = pstats[show].sort_values("PTS", ascending=False).reset_index(drop=True)
st.dataframe(disp, use_container_width=True, hide_index=True)

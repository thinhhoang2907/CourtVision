# pages/2_Team_Stats.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from courtvision.data.nba_client import (
    list_all_teams, recent_seasons,
    get_team_basic_stats, get_team_roster, get_team_players_season_stats, get_team_adv_summary, 
    get_team_record_and_ratings,
)

# Page config
st.set_page_config(layout="wide")

# Enhanced CSS styling
st.markdown("""
    <style>
    .main-header {
        font-size: 3rem;
        font-weight: 700;
        color: #1f77b4;
        margin-bottom: 0.5rem;
    }
    .sub-header {
        font-size: 1.2rem;
        color: #666;
        margin-bottom: 2rem;
    }
    .team-banner {
        background: royalblue;
        padding: 2rem;
        border-radius: 15px;
        margin-bottom: 2rem;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    .metric-card {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #1f77b4;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .leader-card {
        background: royalblue;
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 10px rgba(0,0,0,0.15);
        height: 100%;
    }
    .section-title {
        font-size: 1.8rem;
        font-weight: 600;
        color: #333;
        margin: 2rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 3px solid #1f77b4;
    }
    div[data-testid="stMetricValue"] {
        font-size: 2.5rem;
        font-weight: 700;
    }
    div[data-testid="stMetricLabel"] {
        font-size: 1rem;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.markdown('<h1 class="main-header">Team Statistics</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Comprehensive team performance analysis and player statistics</p>', unsafe_allow_html=True)

st.divider()

# Enhanced Controls
st.markdown("### Select Team & Season")
control_cols = st.columns([3, 2, 1.5])

teams = list_all_teams()
team_name = control_cols[0].selectbox(
    "Team",
    options=[t["full_name"] for t in teams],
    help="Choose a team to view their statistics"
)
season = control_cols[1].selectbox(
    "Season",
    options=recent_seasons(10),
    help="Select the season year"
)
refresh = control_cols[2].button("🔄 Refresh", use_container_width=True)

team = next(t for t in teams if t["full_name"] == team_name)
team_id = team["team_id"]

st.divider()

# Team Banner
st.markdown(f"""
    <div class='team-banner'>
        <h2 style='color: white; margin: 0; font-size: 2.5rem;'>{team_name}</h2>
        <p style='color: rgba(255,255,255,0.9); margin: 0.5rem 0 0 0; font-size: 1.3rem;'>
            {season} Season Analysis
        </p>
    </div>
""", unsafe_allow_html=True)

# Load Dashboard Data
with st.spinner("Loading team performance data..."):
    dash = get_team_record_and_ratings(team_id, season, refresh=refresh)

if dash.empty:
    st.error("Could not load team dashboard for that season.")
    st.stop()

# Extract metrics
W = int(dash.get("W", pd.Series([0])).iloc[0] or 0)
L = int(dash.get("L", pd.Series([0])).iloc[0] or 0)
W_PCT = float(dash.get("W_PCT", pd.Series([0.0])).iloc[0] or 0.0)

OFF_RTG = float(dash.get("OFF_RATING", pd.Series([0.0])).iloc[0] or 0.0)
DEF_RTG = float(dash.get("DEF_RATING", pd.Series([0.0])).iloc[0] or 0.0)
NET_RTG = float(dash.get("NET_RATING", pd.Series([OFF_RTG - DEF_RTG])).iloc[0] or (OFF_RTG - DEF_RTG))

# Key Performance Indicators
st.markdown("### Team Performance")

k1, k2, k3, k4 = st.columns(4)

with k1:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric(
        "Record",
        f"{W}-{L}",
        f"{W_PCT*100:.1f}%",
        help="Win-Loss record and winning percentage"
    )
    st.markdown('</div>', unsafe_allow_html=True)

with k2:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric(
        "Offensive Rating",
        f"{OFF_RTG:.1f}",
        help="Points scored per 100 possessions"
    )
    st.markdown('</div>', unsafe_allow_html=True)

with k3:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    st.metric(
        "Defensive Rating",
        f"{DEF_RTG:.1f}",
        help="Points allowed per 100 possessions"
    )
    st.markdown('</div>', unsafe_allow_html=True)

with k4:
    st.markdown('<div class="metric-card">', unsafe_allow_html=True)
    delta_color = "normal" if NET_RTG >= 0 else "inverse"
    st.metric(
        "Net Rating",
        f"{NET_RTG:.1f}",
        delta_color=delta_color,
        help="Point differential per 100 possessions"
    )
    st.markdown('</div>', unsafe_allow_html=True)

st.divider()

# Player Statistics Section
st.markdown('<p class="section-title">Player Performance</p>', unsafe_allow_html=True)

# Load player stats
with st.spinner("Loading player statistics..."):
    pstats = get_team_players_season_stats(team_id, season, refresh=refresh)

if pstats.empty:
    roster = get_team_roster(team_id, season, refresh=refresh)
    if not roster.empty:
        st.caption("Season player averages unavailable; showing roster instead.")
        st.dataframe(roster, use_container_width=True, hide_index=True)
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
        pstats = pstats.rename(columns={old: new})

# Convert percent decimals to %
for pct_col in ["3P%", "FT%"]:
    if pct_col in pstats.columns:
        pstats[pct_col] = (pstats[pct_col].astype(float) * 100).round(1)

# AST/TO ratio
if "AST" in pstats.columns and "TO" in pstats.columns:
    pstats["AST/TO"] = pstats.apply(
        lambda r: (float(r["AST"]) / float(r["TO"])) if float(r["TO"]) != 0 else None, axis=1
    )
    pstats["AST/TO"] = pstats["AST/TO"].round(2)

# Team Leaders Section
st.markdown("#### Team Leaders")

def _leader(col):
    if col not in pstats.columns: 
        return None
    row = pstats.sort_values(col, ascending=False).head(1)
    return row.iloc[0]["Name"], float(row.iloc[0][col])

leaders = {
    "Points": _leader("PTS"),
    "Rebounds": _leader("REB"),
    "Assists": _leader("AST")
}

lc1, lc2, lc3 = st.columns(3)

for (label, item), col in zip(leaders.items(), [lc1, lc2, lc3]):
    with col:
        if item:
            name, val = item
            st.markdown(f"""
                <div class='leader-card'>
                    <p style='margin: 0; font-size: 0.9rem; opacity: 0.9;'>{label} Leader</p>
                    <h2 style='margin: 0.5rem 0; font-size: 2.5rem;'>{val:.1f}</h2>
                    <p style='margin: 0; font-size: 1.1rem; font-weight: 600;'>{name}</p>
                </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown("""
                <div class='leader-card'>
                    <p style='margin: 0;'>No data available</p>
                </div>
            """, unsafe_allow_html=True)

st.markdown("")  # spacing

# Player Statistics Table
st.markdown("#### Complete Player Statistics")

cols = ["Name", "GP", "MIN", "PTS", "REB", "AST", "STL", "BLK", "3P%", "FT%", "AST/TO"]
show = [c for c in cols if c in pstats.columns]
disp = pstats[show].sort_values("PTS", ascending=False).reset_index(drop=True)

# Enhanced dataframe display with column configuration
st.dataframe(
    disp,
    use_container_width=True,
    hide_index=True,
    column_config={
        "Name": st.column_config.TextColumn("Player", width="medium"),
        "GP": st.column_config.NumberColumn("GP", width="small", help="Games Played"),
        "MIN": st.column_config.NumberColumn("MIN", width="small", help="Minutes Per Game"),
        "PTS": st.column_config.NumberColumn("PTS", width="small", help="Points Per Game"),
        "REB": st.column_config.NumberColumn("REB", width="small", help="Rebounds Per Game"),
        "AST": st.column_config.NumberColumn("AST", width="small", help="Assists Per Game"),
        "STL": st.column_config.NumberColumn("STL", width="small", help="Steals Per Game"),
        "BLK": st.column_config.NumberColumn("BLK", width="small", help="Blocks Per Game"),
        "3P%": st.column_config.NumberColumn("3P%", width="small", format="%.1f%%", help="Three Point Percentage"),
        "FT%": st.column_config.NumberColumn("FT%", width="small", format="%.1f%%", help="Free Throw Percentage"),
        "AST/TO": st.column_config.NumberColumn("AST/TO", width="small", format="%.2f", help="Assist to Turnover Ratio"),
    }
)

# Footer
st.divider()
st.markdown("""
    <div style='text-align: center; color: #888; padding: 1rem;'>
        <p style='margin: 0;'>Data sourced from NBA Stats API</p>
        <p style='margin: 0.5rem 0 0 0; font-size: 0.9rem;'>Statistics updated in real-time</p>
    </div>
""", unsafe_allow_html=True)
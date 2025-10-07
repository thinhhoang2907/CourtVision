import streamlit as st
import pandas as pd
from courtvision.data.nba_client import (
    find_player_basic,
    find_players_by_name,
    get_player_seasons,
    get_player_stats_for_season,
)
from courtvision.data.nba_client import get_player_season_series
import matplotlib.pyplot as plt
import plotly.express as px

st.title("Player Stats")

# search UI
name = st.text_input("Search player by name")
go = st.button("Search")

if go and not name.strip():
    st.warning("Please enter a player name.")
elif go:
    with st.spinner("Searching…"):
        basic = find_player_basic(name.strip())

    if basic is None:
        st.error("No matching player found.")
    else:
        header_cols = st.columns([3, 1.5, 1.5])
        header_cols[0].subheader(basic["full_name"])
        header_cols[1].metric("Team", basic.get("team") or "—")
        header_cols[2].metric("Position", basic.get("position") or "—")

        with st.spinner("Fetching current season totals…"):
            df = get_player_current_season_stats(basic["player_id"])

        if df.empty:
            st.info("No regular-season totals available. Try another player, or check your network.")
        else:
            # nice formatting: order + number formatting
            display = df.copy()
            if "Season" in display.columns:
                season_str = display.iloc[0]["Season"]
                st.caption(f"Most recent season: **{season_str}**")
            st.dataframe(display, hide_index=True, use_container_width=True)

            # optional: quick KPIs
            k1, k2, k3, k4 = st.columns(4)
            for col, label in zip([k1,k2,k3,k4], ["PTS","REB","AST","FG%"]):
                if label in display.columns:
                    val = display.iloc[0][label]
                    col.metric(label, f"{val}")


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
        matches = find_players_by_name(name.strip())

    if not matches:
        st.error("No matching player found.")
    else:
        # if multiple matches, let the user choose
        if len(matches) > 1:
            sel_name = st.selectbox("Multiple matches found — pick a player", [m['full_name'] for m in matches])
            basic = next(m for m in matches if m['full_name'] == sel_name)
        else:
            basic = matches[0]

        header_cols = st.columns([3, 1.5, 1.5])
        header_cols[0].subheader(basic["full_name"])
        header_cols[1].metric("Team", basic.get("team") or "—")
        header_cols[2].metric("Position", basic.get("position") or "—")

        # season selector
        with st.spinner("Fetching available seasons…"):
            seasons = get_player_seasons(basic['player_id'])

        if not seasons:
            st.info("No season data available for this player.")
        else:
            season = st.selectbox("Select season", seasons)

            with st.spinner("Fetching season totals…"):
                df = get_player_stats_for_season(basic['player_id'], season)

            if df.empty:
                st.info("No regular-season totals available for the selected season. Try another player, or check your network.")
            else:
                # nice formatting: order + number formatting
                display = df.copy()
                if "Season" in display.columns:
                    season_str = display.iloc[0]["Season"]
                    st.caption(f"Selected season: **{season_str}**")
                st.dataframe(display, hide_index=True, width='stretch')

                # optional: quick KPIs
                k1, k2, k3, k4 = st.columns(4)
                for col, label in zip([k1,k2,k3,k4], ["PTS","REB","AST","FG%"]):
                    if label in display.columns:
                        val = display.iloc[0][label]
                        col.metric(label, f"{val}")

                # --- Visualizations: per-season per-game PTS (Matplotlib + Plotly)
                series = get_player_season_series(basic['player_id'])
                if not series.empty and 'PTS' in series.columns:
                    # ensure seasons as labels
                    seasons = list(series['Season'].astype(str))
                    pts = list(series['PTS'].astype(float))

                    st.markdown('### Scoring by season')
                    fig, ax = plt.subplots()
                    ax.bar(seasons, pts, color='C0')
                    ax.set_xlabel('Season')
                    ax.set_ylabel('PTS per game')
                    ax.set_title(f"{basic['full_name']} - PTS per game by season")
                    plt.xticks(rotation=45)
                    st.pyplot(fig)

                    # line chart for trend
                    fig2, ax2 = plt.subplots()
                    ax2.plot(seasons, pts, marker='o')
                    ax2.set_xlabel('Season')
                    ax2.set_ylabel('PTS per game')
                    ax2.set_title(f"{basic['full_name']} - Career PTS trend")
                    plt.xticks(rotation=45)
                    st.pyplot(fig2)

                    # Plotly interactive versions
                    with st.expander('Interactive charts (Plotly)'):
                        dfp = series[['Season','PTS']].copy()
                        dfp['Season'] = dfp['Season'].astype(str)
                        bar = px.bar(dfp, x='Season', y='PTS', title=f"{basic['full_name']} - PTS per game by season")
                        line = px.line(dfp, x='Season', y='PTS', title=f"{basic['full_name']} - Career PTS trend", markers=True)
                        st.plotly_chart(bar, use_container_width=True)
                        st.plotly_chart(line, use_container_width=True)


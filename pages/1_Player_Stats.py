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

name = st.text_input("Search player by name", "LeBron James")
if st.button("Search") and name.strip():
    basic = find_player_basic(name)
    if basic is None:
        st.error("No matching player found.")
    else:
        st.subheader(f"{basic['full_name']} — {basic.get('team','?')} ({basic.get('position','?')})")
        df = get_player_current_season_stats(basic["player_id"])
        st.dataframe(df)

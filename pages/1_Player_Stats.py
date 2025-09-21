import streamlit as st
import pandas as pd
from courtvision.data.nba_client import find_player_basic, get_player_current_season_stats

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

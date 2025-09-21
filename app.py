import streamlit as st

st.set_page_config(page_title="CourtVision", page_icon="🏀", layout="wide")
st.sidebar.title("CourtVision")
st.sidebar.markdown("Navigation:\n- Player Stats\n- Team Stats\n- Comparisons")

st.title("CourtVision")
st.write("Welcome! Use the sidebar to navigate: Player Stats, Team Stats, Comparisons.")
st.write("This app provides basketball statistics and visualizations.")
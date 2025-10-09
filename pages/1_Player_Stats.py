import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
#from courtvision.data.nba_client import find_player_basic, get_player_current_season_stats
from courtvision.data.nba_client import (
    list_all_teams, team_players_for_dropdown, search_players,
    get_player_card, list_seasons_for_player, get_player_season_totals,
    player_career_pts_fg, recent_seasons,
)

st.title("Player Stats")

# Controls
cols = st.columns([1.5, 1, 2, 1])
teams = list_all_teams()
team_options = ["— All Teams —"] + [t["full_name"] for t in teams]
team_name = cols[0].selectbox("Filter by Team (optional)", options=team_options)
team_season = cols[1].selectbox("Team Season (for roster filter)", options=recent_seasons(10))
query = cols[2].text_input("…or search by name (press Enter)")
refresh = cols[3].button("Refresh from API")

# Build choices (team roster first; fallback to name search)
choices = []
if team_name != "— All Teams —":
    team = next(t for t in teams if t["full_name"] == team_name)
    roster = team_players_for_dropdown(team["team_id"], team_season, refresh=refresh)
    choices = [f"{p['full_name']} (id={p['player_id']})" for p in roster]

if query.strip():
    matches = search_players(query.strip())
    # Append matches; avoid duplicates
    seen = set(choices)
    for m in matches:
        label = f"{m['full_name']} (id={m['player_id']})"
        if label not in seen:
            choices.append(label); seen.add(label)

if not choices:
    st.info("Pick a team to filter the roster, or type a player name.")
    st.stop()

idx = st.selectbox("Select a player", options=list(range(len(choices))), format_func=lambda i: choices[i])
sel = choices[idx]
try:
    player_id = int(sel.split("(id=")[1].split(")")[0])
except Exception:
    st.error(f"Could not parse player id from: {sel}")
    st.stop()

# Card & seasons
card = get_player_card(player_id, refresh=refresh)
c1, c2, c3 = st.columns([3,1,1])
c1.subheader(card.get("full_name",""))
c2.metric("Team", card.get("team") or "—")
c3.metric("Position", card.get("position") or "—")

seasons = list_seasons_for_player(player_id, refresh=refresh)
if not seasons:
    st.error("No seasons found for this player.")
    st.stop()

season = st.selectbox("Season", options=list(reversed(seasons)))

# Season totals
with st.spinner("Loading season totals…"):
    totals = get_player_season_totals(player_id, season, refresh=refresh)

if totals.empty:
    st.info("No season totals available.")
else:
    # Convert season totals to per-game (PPG/RPG/APG/SPG/BPG) for display
    row = totals.iloc[0]
    # Determine games played column
    gp_val = None
    for col in ("GP", "G"):
        if col in row.index:
            try:
                gp_val = float(row[col])
            except Exception:
                gp_val = None
            break

    def per_game(stat_name):
        if gp_val and gp_val > 0 and stat_name in row.index:
            try:
                return round(float(row[stat_name]) / gp_val, 1)
            except Exception:
                return "—"
        return "—"

    ppg = per_game("PTS")
    rpg = per_game("REB")
    apg = per_game("AST")
    spg = per_game("STL")
    bpg = per_game("BLK")

    # Show a compact per-game summary table instead of raw season totals
    display_row = {
        "Season": row.get("Season", ""),
        "Team": row.get("Team", ""),
        "GP": int(gp_val) if gp_val is not None else "—",
        "MP": row.get("MP", "—"),
        "PPG": ppg,
        "RPG": rpg,
        "APG": apg,
        "SPG": spg,
        "BPG": bpg,
        "FG%": row.get("FG%", "—"),
    }
    st.dataframe(pd.DataFrame([display_row]), use_container_width=True, hide_index=True)

    k1,k2,k3,k4,k5 = st.columns(5)
    k1.metric("PPG", str(ppg))
    k2.metric("RPG", str(rpg))
    k3.metric("APG", str(apg))
    k4.metric("SPG", str(spg))
    k5.metric("BPG", str(bpg))
    

# Charts
st.markdown("### Career Trends")
series = player_career_pts_fg(player_id, refresh=refresh)
if series.empty or "Season" not in series.columns:
    st.info("Not enough data to chart.")
else:
    s = series.sort_values("Season")
    # Compute PPG safely using GP if present
    def compute_ppg(row):
        gp = None
        for col in ("GP", "G"):
            if col in row.index:
                try:
                    gp = float(row[col])
                except Exception:
                    gp = None
                break
        try:
            if gp and gp > 0:
                return float(row.get("PTS", 0)) / gp
            # fall back to totals if GP not available
            return float(row.get("PTS", 0))
        except Exception:
            return None

    s = s.copy()
    s["PPG"] = s.apply(compute_ppg, axis=1)

    # Create two side-by-side charts: PPG and FG%
    c1, c2 = st.columns(2)

    with c1:
        fig1 = plt.figure(figsize=(6, 3))
        plt.bar(s["Season"], s["PPG"].round(1))
        plt.xticks(rotation=45, ha="right"); plt.ylabel("PPG"); plt.title("Points Per Game by Season")
        st.pyplot(fig1, clear_figure=True)

    with c2:
        fig2 = plt.figure(figsize=(6, 3))
        plt.plot(s["Season"], s["FG%"], marker="o")
        plt.xticks(rotation=45, ha="right"); plt.ylabel("Field Goal %"); plt.title("FG% by Season")
        st.pyplot(fig2, clear_figure=True)


# # search UI
# name = st.text_input("Search player by name")
# go = st.button("Search")

# if go and not name.strip():
#     st.warning("Please enter a player name.")
# elif go:
#     with st.spinner("Searching…"):
#         basic = find_player_basic(name.strip())

#     if basic is None:
#         st.error("No matching player found.")
#     else:
#         header_cols = st.columns([3, 1.5, 1.5])
#         header_cols[0].subheader(basic["full_name"])
#         header_cols[1].metric("Team", basic.get("team") or "—")
#         header_cols[2].metric("Position", basic.get("position") or "—")

#         with st.spinner("Fetching current season totals…"):
#             df = get_player_current_season_stats(basic["player_id"])

#         if df.empty:
#             st.info("No regular-season totals available. Try another player, or check your network.")
#         else:
#             # nice formatting: order + number formatting
#             display = df.copy()
#             if "Season" in display.columns:
#                 season_str = display.iloc[0]["Season"]
#                 st.caption(f"Most recent season: **{season_str}**")
#             st.dataframe(display, hide_index=True, use_container_width=True)

#             # optional: quick KPIs
#             # show common per-game metrics if available
#             k1, k2, k3, k4, k5 = st.columns(5)
#             labels = ["PPG","RPG","APG","SPG","BPG"]
#             cols = [k1, k2, k3, k4, k5]
#             for col_widget, label in zip(cols, labels):
#                 if label in display.columns:
#                     val = display.iloc[0][label]
#                     col_widget.metric(label, f"{val}")

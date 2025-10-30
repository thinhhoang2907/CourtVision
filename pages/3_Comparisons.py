# pages/3_Comparisons.py
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from courtvision.data.nba_client import (
    list_all_teams, recent_seasons, search_players, team_players_for_dropdown,
    list_seasons_for_player, get_player_season_row, get_team_season_base_totals,
    compute_usage_rate, compute_true_shooting_pct,
    get_team_record_and_ratings, get_team_h2h_games, compute_player_PER
)

st.title("Comparisons")

mode = st.radio("Compare", ["Players", "Teams"], horizontal=True)
refresh = st.button("Refresh from API")

# ---------- helpers ----------
def pick_by_name(col, label):
    name = col.text_input(f"{label} — search by name")
    if not name.strip():
        return None
    matches = search_players(name.strip())
    options = [f"{m['full_name']} (id={m['player_id']})" for m in matches]
    if not options:
        col.info("No matches.")
        return None
    idx = col.selectbox(label, list(range(len(options))), format_func=lambda i: options[i], key=label)
    return int(options[idx].split("(id=")[1].split(")")[0])

def first_available_season(player_id, preferred_season):
    """Return (season_to_use, is_exact) for a player, falling back to most recent season."""
    seasons = list(reversed(list_seasons_for_player(player_id, refresh=refresh)))  # newest -> oldest
    if not seasons:
        return None, False
    if preferred_season in seasons:
        return preferred_season, True
    return seasons[0], False

def per_game_from_row(r, stat):
    if r.empty: return None
    gp = float(r.iloc[0].get("GP", 0) or 0)
    val = float(r.iloc[0].get(stat, 0) or 0)
    return round(val / gp, 1) if gp > 0 else None

def team_id_from_row(row):
    if row.empty: return None
    if "TEAM_ID" in row.columns:
        return int(row["TEAM_ID"].iloc[0])
    # if missing, we’ll skip USG%
    return None

# ---------- PLAYERS MODE ----------
if mode == "Players":
    seasons = recent_seasons(10)
    # Controls row: center season selector
    st.write("")
    top = st.columns([1,1,1])
    season = top[1].selectbox("Season", options=seasons)

    # Two big columns: Left = Player A, Right = Player B  ✅ (swapped)
    col_left, col_right = st.columns(2)

    # Player A (left side)
    with col_left:
        st.subheader("Player A")
        teams = list_all_teams()
        team_opts = ["— All Teams —"] + [t["full_name"] for t in teams]
        team_filter_a = st.selectbox("Filter by Team (optional)", team_opts, key="teamA")
        if team_filter_a != "— All Teams —":
            t = next(t for t in teams if t["full_name"] == team_filter_a)
            roster = team_players_for_dropdown(t["team_id"], season, refresh=refresh)
            opts = [f"{p['full_name']} (id={p['player_id']})" for p in roster]
            pid_a = None
            if opts:
                idx = st.selectbox("Player A", list(range(len(opts))), format_func=lambda i: opts[i], key="pickA")
                pid_a = int(opts[idx].split("(id=")[1].split(")")[0])
            else:
                pid_a = pick_by_name(st, "Player A")
        else:
            pid_a = pick_by_name(st, "Player A")

    # Player B (right side)
    with col_right:
        st.subheader("Player B")
        teams = list_all_teams()
        team_opts = ["— All Teams —"] + [t["full_name"] for t in teams]
        team_filter_b = st.selectbox("Filter by Team (optional)", team_opts, key="teamB")
        if team_filter_b != "— All Teams —":
            t = next(t for t in teams if t["full_name"] == team_filter_b)
            roster = team_players_for_dropdown(t["team_id"], season, refresh=refresh)
            opts = [f"{p['full_name']} (id={p['player_id']})" for p in roster]
            pid_b = None
            if opts:
                idx = st.selectbox("Player B", list(range(len(opts))), format_func=lambda i: opts[i], key="pickB")
                pid_b = int(opts[idx].split("(id=")[1].split(")")[0])
            else:
                pid_b = pick_by_name(st, "Player B")
        else:
            pid_b = pick_by_name(st, "Player B")

    if not pid_a or not pid_b:
        st.info("Select two players to compare.")
        st.stop()

    # Resolve which season we can actually use for each player
    season_a, exact_a = first_available_season(pid_a, season)
    season_b, exact_b = first_available_season(pid_b, season)

    # Load rows (totals) for those seasons
    row_a = get_player_season_row(pid_a, season_a, refresh=refresh)
    row_b = get_player_season_row(pid_b, season_b, refresh=refresh)

    # Compute per-game basics
    ppg_a = per_game_from_row(row_a, "PTS"); rpg_a = per_game_from_row(row_a, "REB")
    apg_a = per_game_from_row(row_a, "AST"); spg_a = per_game_from_row(row_a, "STL")
    bpg_a = per_game_from_row(row_a, "BLK")

    ppg_b = per_game_from_row(row_b, "PTS"); rpg_b = per_game_from_row(row_b, "REB")
    apg_b = per_game_from_row(row_b, "AST"); spg_b = per_game_from_row(row_b, "STL")
    bpg_b = per_game_from_row(row_b, "BLK")

    # USG% (needs team totals)
    tid_a = team_id_from_row(row_a); tid_b = team_id_from_row(row_b)
    team_tot_a = get_team_season_base_totals(tid_a, season_a, refresh=refresh) if tid_a else pd.DataFrame()
    team_tot_b = get_team_season_base_totals(tid_b, season_b, refresh=refresh) if tid_b else pd.DataFrame()
    usg_a = compute_usage_rate(row_a, team_tot_a)
    usg_b = compute_usage_rate(row_b, team_tot_b)

    # --- Advanced metrics (TS% & PER) ---
    ts_a = compute_true_shooting_pct(row_a)
    ts_b = compute_true_shooting_pct(row_b)

    # For PER we need team totals (for same season actually used)
    tid_a = team_id_from_row(row_a)
    tid_b = team_id_from_row(row_b)
    team_tot_a = get_team_season_base_totals(tid_a, season_a, refresh=refresh) if tid_a else pd.DataFrame()
    team_tot_b = get_team_season_base_totals(tid_b, season_b, refresh=refresh) if tid_b else pd.DataFrame()

    per_a = compute_player_PER(row_a, team_tot_a, season_a, refresh=refresh)
    per_b = compute_player_PER(row_b, team_tot_b, season_b, refresh=refresh)


    # Build table (A on Left, B on Right)
    display = pd.DataFrame([
        {"Metric": "Season used",   "Left": season_a + ("" if exact_a else " *"), "Right": season_b + ("" if exact_b else " *")},
        {"Metric": "PPG / RPG / APG / SPG / BPG",
         "Left":  f"{ppg_a}/{rpg_a}/{apg_a}/{spg_a}/{bpg_a}",
         "Right": f"{ppg_b}/{rpg_b}/{apg_b}/{spg_b}/{bpg_b}"},
        {"Metric": "USG%",          "Left": f"{usg_a:.1f}%" if usg_a is not None else "—",
                                    "Right": f"{usg_b:.1f}%" if usg_b is not None else "—"},
        {"Metric": "True Shooting", "Left": f"{ts_a:.1f}%" if ts_a is not None else "—",
                                    "Right": f"{ts_b:.1f}%" if ts_b is not None else "—"},
        {"Metric": "PER (approx)",  "Left": f"{per_a:.1f}" if per_a is not None else "—",
                                    "Right": f"{per_b:.1f}" if per_b is not None else "—"},
    ])

    st.subheader("Player vs Player")
    st.dataframe(display, use_container_width=True, hide_index=True)
    st.caption("*Season marked with an asterisk (*) means your chosen season wasn’t available; used the player’s most recent season instead.\nPER is computed using the full Hollinger/BBR formula (uPER → pace adjustment → normalized to league average = 15).")


# ---------- TEAMS MODE (unchanged from your working version) ----------
# ---------- TEAMS MODE ----------
else:
    col = st.columns(3)
    season = col[1].selectbox("Season", options=recent_seasons(10))

    # Load all teams and build name→team mapping
    teams = list_all_teams()
    team_names = [t["full_name"] for t in teams]
    name_to_team = {t["full_name"]: t for t in teams}

    # Dropdowns for selecting teams
    team_left  = col[0].selectbox("Left Team",  options=team_names)
    team_right = col[2].selectbox("Right Team", options=team_names)

    # Get the full team info safely
    tA = name_to_team.get(team_left)
    tB = name_to_team.get(team_right)

    # Helper to handle possible missing keys
    def _team_id_safe(t):
        if isinstance(t, dict):
            for k in ("team_id", "TEAM_ID", "id"):
                if k in t and t[k] is not None:
                    return int(t[k])
        return None

    # ✅ DEFINE IDs HERE — these are what we’ll use everywhere
    team_id_left  = _team_id_safe(tA)
    team_id_right = _team_id_safe(tB)

    if team_id_left is None or team_id_right is None:
        st.error("Could not resolve team IDs. Click 'Refresh from API' and try again.")
        st.stop()

    # --- Team summary data ---
    with st.spinner("Loading team summaries…"):
        A = get_team_record_and_ratings(team_id_left, season, refresh=refresh)
        B = get_team_record_and_ratings(team_id_right, season, refresh=refresh)

    if A.empty or B.empty:
        st.error("Could not load team summaries.")
        st.stop()

    # --- Compute ratings for tiles ---
    def _g(df, col, default=None):
        return float(df.get(col, pd.Series([default])).iloc[0] or default)

    W_A = int(A.get("W", pd.Series([0])).iloc[0] or 0)
    L_A = int(A.get("L", pd.Series([0])).iloc[0] or 0)
    W_B = int(B.get("W", pd.Series([0])).iloc[0] or 0)
    L_B = int(B.get("L", pd.Series([0])).iloc[0] or 0)

    ORtg_A = _g(A, "OFF_RATING", 0.0)
    DRtg_A = _g(A, "DEF_RATING", 0.0)
    NRtg_A = _g(A, "NET_RATING", ORtg_A - DRtg_A)

    ORtg_B = _g(B, "OFF_RATING", 0.0)
    DRtg_B = _g(B, "DEF_RATING", 0.0)
    NRtg_B = _g(B, "NET_RATING", ORtg_B - DRtg_B)

    st.subheader("Team vs Team")
    k1,k2,k3,k4 = st.columns(4)
    k1.metric(f"{team_left} Record",  f"{W_A}-{L_A}")
    k2.metric(f"{team_right} Record", f"{W_B}-{L_B}")
    k3.metric("Net Rating (Left)",  f"{NRtg_A:.1f}")
    k4.metric("Net Rating (Right)", f"{NRtg_B:.1f}")

    # --- Head-to-Head section ---
    with st.spinner("Computing head-to-head…"):
        h2h_sum, h2h_games = get_team_h2h_games(team_id_left, team_id_right, season, refresh=refresh)

    st.markdown(f"### Head-to-Head {season}")
    st.markdown(f"**{team_left} {h2h_sum['A_wins']} – {h2h_sum['B_wins']} {team_right}**  (Games: {h2h_sum['games']})")

    if not h2h_games.empty:
        def _res(row):
            return f"{team_left} {int(row['PTS_A'])}, {team_right} {int(row['PTS_B'])}"
        display_games = pd.DataFrame({
            "Date": pd.to_datetime(h2h_games["GAME_DATE"], errors='coerce').dt.strftime("%b %d"),
            "Result": h2h_games.apply(_res, axis=1),
        })
        st.dataframe(display_games, use_container_width=True, hide_index=True)
    else:
        st.caption("No regular-season head-to-head games found for this season.")

    # --- Ratings comparison table ---
    comp = pd.DataFrame([
        {"Metric": "Off Rating", "Left": f"{ORtg_A:.1f}", "Right": f"{ORtg_B:.1f}"},
        {"Metric": "Def Rating", "Left": f"{DRtg_A:.1f}", "Right": f"{DRtg_B:.1f}"},
        {"Metric": "Net Rating", "Left": f"{NRtg_A:.1f}", "Right": f"{NRtg_B:.1f}"},
    ])
    st.dataframe(comp, use_container_width=True, hide_index=True)

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
    .comparison-card {
        background: steelblue;
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 10px rgba(0,0,0,0.15);
        margin-bottom: 1rem;
    }
    .vs-divider {
        font-size: 2.5rem;
        font-weight: 700;
        color: #1f77b4;
        text-align: center;
        padding: 2rem 0;
    }
    .section-title {
        font-size: 1.8rem;
        font-weight: 600;
        color: #333;
        margin: 2rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 3px solid #1f77b4;
    }
    .player-selector-card {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #667eea;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .team-selector-card {
        background: #f8f9fa;
        padding: 1.5rem;
        border-radius: 10px;
        border-left: 4px solid #764ba2;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
    }
    .metric-highlight {
        background: #fff;
        padding: 1rem;
        border-radius: 8px;
        margin: 0.5rem 0;
        border-left: 3px solid #1f77b4;
    }
    .h2h-summary {
        background: steelblue;
        padding: 1.5rem;
        border-radius: 12px;
        color: white;
        text-align: center;
        font-size: 1.5rem;
        font-weight: 600;
        margin: 1rem 0;
    }
    /* Hide the progress bars in metric cards */
    div[data-testid="stMetric"] > div > div > div:first-child {
        display: none;
    }
    </style>
""", unsafe_allow_html=True)

# Header
st.markdown('<h1 class="main-header">Player & Team Comparisons</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Head-to-head analysis and performance comparisons</p>', unsafe_allow_html=True)

st.divider()

# Mode Selection
mode_col1, mode_col2, mode_col3 = st.columns([1, 2, 1])
with mode_col2:
    mode = st.radio(
        "Select Comparison Type",
        ["Players", "Teams"],
        horizontal=True,
        label_visibility="collapsed"
    )

refresh_col1, refresh_col2, refresh_col3 = st.columns([1, 1, 1])
with refresh_col2:
    refresh = st.button("🔄 Refresh Data", use_container_width=True)

st.divider()

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
    seasons = list(reversed(list_seasons_for_player(player_id, refresh=refresh)))
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
    return None

# ---------- PLAYERS MODE ----------
if mode == "Players":
    # Season selector centered
    season_cols = st.columns([1, 2, 1])
    with season_cols[1]:
        seasons = recent_seasons(10)
        season = st.selectbox("Season", options=seasons, label_visibility="visible")

    st.markdown("")
    
    # Two columns for player selection
    col_left, col_right = st.columns(2)

    # Player A (left side)
    with col_left:
        st.markdown('<div class="player-selector-card">', unsafe_allow_html=True)
        st.markdown("#### Player A")
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
        st.markdown('</div>', unsafe_allow_html=True)

    # Player B (right side)
    with col_right:
        st.markdown('<div class="player-selector-card">', unsafe_allow_html=True)
        st.markdown("#### Player B")
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
        st.markdown('</div>', unsafe_allow_html=True)

    if not pid_a or not pid_b:
        st.info("Select two players to compare.")
        st.stop()

    # Resolve seasons
    season_a, exact_a = first_available_season(pid_a, season)
    season_b, exact_b = first_available_season(pid_b, season)

    # Load player data
    row_a = get_player_season_row(pid_a, season_a, refresh=refresh)
    row_b = get_player_season_row(pid_b, season_b, refresh=refresh)

    # Get player names
    from courtvision.data.nba_client import get_player_card
    card_a = get_player_card(pid_a, refresh=refresh)
    card_b = get_player_card(pid_b, refresh=refresh)
    name_a = card_a.get("full_name", f"Player {pid_a}")
    name_b = card_b.get("full_name", f"Player {pid_b}")

    st.divider()

    # Player comparison header
    header_col1, header_col2, header_col3 = st.columns([1, 0.3, 1])
    
    with header_col1:
        st.markdown(f"""
            <div class='comparison-card'>
                <h2 style='margin: 0; font-size: 2rem;'>{name_a}</h2>
                <p style='margin: 0.5rem 0 0 0; font-size: 1.1rem; opacity: 0.9;'>{season_a}{'*' if not exact_a else ''}</p>
            </div>
        """, unsafe_allow_html=True)
    
    with header_col2:
        st.markdown('<div class="vs-divider">VS</div>', unsafe_allow_html=True)
    
    with header_col3:
        st.markdown(f"""
            <div class='comparison-card'>
                <h2 style='margin: 0; font-size: 2rem;'>{name_b}</h2>
                <p style='margin: 0.5rem 0 0 0; font-size: 1.1rem; opacity: 0.9;'>{season_b}{'*' if not exact_b else ''}</p>
            </div>
        """, unsafe_allow_html=True)

    # Compute stats
    ppg_a = per_game_from_row(row_a, "PTS"); rpg_a = per_game_from_row(row_a, "REB")
    apg_a = per_game_from_row(row_a, "AST"); spg_a = per_game_from_row(row_a, "STL")
    bpg_a = per_game_from_row(row_a, "BLK")

    ppg_b = per_game_from_row(row_b, "PTS"); rpg_b = per_game_from_row(row_b, "REB")
    apg_b = per_game_from_row(row_b, "AST"); spg_b = per_game_from_row(row_b, "STL")
    bpg_b = per_game_from_row(row_b, "BLK")

    # Advanced stats
    tid_a = team_id_from_row(row_a); tid_b = team_id_from_row(row_b)
    team_tot_a = get_team_season_base_totals(tid_a, season_a, refresh=refresh) if tid_a else pd.DataFrame()
    team_tot_b = get_team_season_base_totals(tid_b, season_b, refresh=refresh) if tid_b else pd.DataFrame()
    usg_a = compute_usage_rate(row_a, team_tot_a)
    usg_b = compute_usage_rate(row_b, team_tot_b)
    ts_a = compute_true_shooting_pct(row_a)
    ts_b = compute_true_shooting_pct(row_b)
    per_a = compute_player_PER(row_a, team_tot_a, season_a, refresh=refresh)
    per_b = compute_player_PER(row_b, team_tot_b, season_b, refresh=refresh)

    # Comparison Table
    st.markdown('<p class="section-title">Statistical Comparison</p>', unsafe_allow_html=True)
    
    display = pd.DataFrame([
        {"Metric": "Season used", "Player A": season_a + ("*" if not exact_a else ""), "Player B": season_b + ("*" if not exact_b else "")},
        {"Metric": "PPG / RPG / APG / SPG / BPG",
         "Player A": f"{ppg_a}/{rpg_a}/{apg_a}/{spg_a}/{bpg_a}",
         "Player B": f"{ppg_b}/{rpg_b}/{apg_b}/{spg_b}/{bpg_b}"},
        {"Metric": "Usage Rate", "Player A": f"{usg_a:.1f}%" if usg_a is not None else "—",
                                 "Player B": f"{usg_b:.1f}%" if usg_b is not None else "—"},
        {"Metric": "True Shooting %", "Player A": f"{ts_a:.1f}%" if ts_a is not None else "—",
                                      "Player B": f"{ts_b:.1f}%" if ts_b is not None else "—"},
        {"Metric": "PER (approx)", "Player A": f"{per_a:.1f}" if per_a is not None else "—",
                                   "Player B": f"{per_b:.1f}" if per_b is not None else "—"},
    ])

    st.dataframe(
        display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Metric": st.column_config.TextColumn("Metric", width="medium"),
            "Player A": st.column_config.TextColumn(name_a, width="medium"),
            "Player B": st.column_config.TextColumn(name_b, width="medium"),
        }
    )
    
    st.caption("*Season marked with an asterisk means your chosen season wasn't available; used the player's most recent season instead.")
    st.caption("PER is computed using the full Hollinger/BBR formula (uPER → pace adjustment → normalized to league average = 15).")

# ---------- TEAMS MODE ----------
else:
    # Season selector centered
    season_cols = st.columns([1, 2, 1])
    with season_cols[1]:
        season = st.selectbox("Season", options=recent_seasons(10))

    st.markdown("")

    # Load teams
    teams = list_all_teams()
    team_names = [t["full_name"] for t in teams]
    name_to_team = {t["full_name"]: t for t in teams}

    # Two columns for team selection
    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown('<div class="team-selector-card">', unsafe_allow_html=True)
        st.markdown("#### Team A")
        team_left = st.selectbox("Select First Team", options=team_names, key="team_left")
        st.markdown('</div>', unsafe_allow_html=True)

    with col_right:
        st.markdown('<div class="team-selector-card">', unsafe_allow_html=True)
        st.markdown("#### Team B")
        team_right = st.selectbox("Select Second Team", options=team_names, key="team_right")
        st.markdown('</div>', unsafe_allow_html=True)

    # Get team info
    tA = name_to_team.get(team_left)
    tB = name_to_team.get(team_right)

    def _team_id_safe(t):
        if isinstance(t, dict):
            for k in ("team_id", "TEAM_ID", "id"):
                if k in t and t[k] is not None:
                    return int(t[k])
        return None

    team_id_left = _team_id_safe(tA)
    team_id_right = _team_id_safe(tB)

    if team_id_left is None or team_id_right is None:
        st.error("Could not resolve team IDs. Click 'Refresh Data' and try again.")
        st.stop()

    st.divider()

    # Team comparison header
    header_col1, header_col2, header_col3 = st.columns([1, 0.3, 1])
    
    with header_col1:
        st.markdown(f"""
            <div class='comparison-card'>
                <h2 style='margin: 0; font-size: 2rem;'>{team_left}</h2>
                <p style='margin: 0.5rem 0 0 0; font-size: 1.1rem; opacity: 0.9;'>{season} Season</p>
            </div>
        """, unsafe_allow_html=True)
    
    with header_col2:
        st.markdown('<div class="vs-divider">VS</div>', unsafe_allow_html=True)
    
    with header_col3:
        st.markdown(f"""
            <div class='comparison-card'>
                <h2 style='margin: 0; font-size: 2rem;'>{team_right}</h2>
                <p style='margin: 0.5rem 0 0 0; font-size: 1.1rem; opacity: 0.9;'>{season} Season</p>
            </div>
        """, unsafe_allow_html=True)

    # Load team data
    with st.spinner("Loading team summaries..."):
        A = get_team_record_and_ratings(team_id_left, season, refresh=refresh)
        B = get_team_record_and_ratings(team_id_right, season, refresh=refresh)

    if A.empty or B.empty:
        st.error("Could not load team summaries.")
        st.stop()

    # Extract metrics
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

    # Season Records
    st.markdown('<p class="section-title">Season Performance</p>', unsafe_allow_html=True)
    
    rec_col1, rec_col2, rec_col3, rec_col4 = st.columns(4)
    rec_col1.metric(f"{team_left} Record", f"{W_A}-{L_A}")
    rec_col2.metric(f"{team_right} Record", f"{W_B}-{L_B}")
    rec_col3.metric("Net Rating (Team A)", f"{NRtg_A:.1f}")
    rec_col4.metric("Net Rating (Team B)", f"{NRtg_B:.1f}")

    st.divider()

    # Head-to-Head section
    with st.spinner("Computing head-to-head..."):
        h2h_sum, h2h_games = get_team_h2h_games(team_id_left, team_id_right, season, refresh=refresh)

    st.markdown('<p class="section-title">Head-to-Head Matchup</p>', unsafe_allow_html=True)
    
    st.markdown(f"""
        <div class='h2h-summary'>
            {team_left}: {h2h_sum['A_wins']} — {h2h_sum['B_wins']} :{team_right}
            <br>
            <span style='font-size: 1rem; opacity: 0.9;'>Total Games: {h2h_sum['games']}</span>
        </div>
    """, unsafe_allow_html=True)

    if not h2h_games.empty:
        st.markdown("#### Game Results")
        def _res(row):
            return f"{team_left} {int(row['PTS_A'])}, {team_right} {int(row['PTS_B'])}"
        display_games = pd.DataFrame({
            "Date": pd.to_datetime(h2h_games["GAME_DATE"], errors='coerce').dt.strftime("%b %d"),
            "Result": h2h_games.apply(_res, axis=1),
        })
        st.dataframe(
            display_games,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Date": st.column_config.TextColumn("Date", width="small"),
                "Result": st.column_config.TextColumn("Score", width="large"),
            }
        )
    else:
        st.caption("No regular-season head-to-head games found for this season.")

    st.divider()

    # Ratings comparison table
    st.markdown('<p class="section-title">Advanced Ratings Comparison</p>', unsafe_allow_html=True)
    
    comp = pd.DataFrame([
        {"Metric": "Offensive Rating", team_left: f"{ORtg_A:.1f}", team_right: f"{ORtg_B:.1f}"},
        {"Metric": "Defensive Rating", team_left: f"{DRtg_A:.1f}", team_right: f"{DRtg_B:.1f}"},
        {"Metric": "Net Rating", team_left: f"{NRtg_A:.1f}", team_right: f"{NRtg_B:.1f}"},
    ])
    st.dataframe(
        comp,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Metric": st.column_config.TextColumn("Metric", width="medium"),
            team_left: st.column_config.TextColumn(team_left, width="medium"),
            team_right: st.column_config.TextColumn(team_right, width="medium"),
        }
    )

# Footer
st.divider()
st.markdown("""
    <div style='text-align: center; color: #888; padding: 1rem;'>
        <p style='margin: 0;'>Data sourced from NBA Stats API</p>
        <p style='margin: 0.5rem 0 0 0; font-size: 0.9rem;'>Advanced metrics calculated using industry-standard formulas</p>
    </div>
""", unsafe_allow_html=True)
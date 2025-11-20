import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from courtvision.data.nba_client import (
    list_all_teams, team_players_for_dropdown, search_players,
    get_player_card, list_seasons_for_player, get_player_season_totals,
    player_career_pts_fg, recent_seasons,
)

# Page config
st.set_page_config(layout="wide")

# Custom CSS for better styling
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
    .stat-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1.5rem;
        border-radius: 10px;
        color: white;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .metric-container {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #1f77b4;
    }
    div[data-testid="stMetricValue"] {
        font-size: 2rem;
        font-weight: 600;
    }
    .dataframe {
        font-size: 0.95rem;
    }
    .chart-title {
        font-size: 1.3rem;
        font-weight: 600;
        color: #333;
        margin-bottom: 1rem;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<h1 class="main-header">Player Statistics</h1>', unsafe_allow_html=True)
st.markdown('<p class="sub-header">Search and analyze individual player performance across seasons</p>', unsafe_allow_html=True)

st.divider()

# Controls with better organization
st.markdown("### Search & Filter")
cols = st.columns([2, 1.5, 2.5, 1])

teams = list_all_teams()
team_options = ["— All Teams —"] + [t["full_name"] for t in teams]
team_name = cols[0].selectbox("Filter by Team", options=team_options)
team_season = cols[1].selectbox("Team Season", options=recent_seasons(10))
query = cols[2].text_input("Search by Player Name", placeholder="e.g., LeBron James")
refresh = cols[3].button("🔄 Refresh", use_container_width=True)

# Build choices (team roster first; fallback to name search)
choices = []
if team_name != "— All Teams —":
    team = next(t for t in teams if t["full_name"] == team_name)
    roster = team_players_for_dropdown(team["team_id"], team_season, refresh=refresh)
    choices = [f"{p['full_name']} (id={p['player_id']})" for p in roster]

if query.strip():
    matches = search_players(query.strip())
    seen = set(choices)
    for m in matches:
        label = f"{m['full_name']} (id={m['player_id']})"
        if label not in seen:
            choices.append(label)
            seen.add(label)

if not choices:
    st.info("👆 Select a team or enter a player name to begin")
    st.stop()

idx = st.selectbox("Select Player", options=list(range(len(choices))), format_func=lambda i: choices[i])
sel = choices[idx]
try:
    player_id = int(sel.split("(id=")[1].split(")")[0])
except Exception:
    st.error(f"Could not parse player id from: {sel}")
    st.stop()

st.divider()

# Card & seasons
card = get_player_card(player_id, refresh=refresh)

# Player Header with enhanced styling
st.markdown(f"""
    <div style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); 
                padding: 2rem; 
                border-radius: 15px; 
                margin-bottom: 2rem;
                box-shadow: 0 4px 15px rgba(0,0,0,0.2);'>
        <h2 style='color: white; margin: 0; font-size: 2.5rem;'>{card.get("full_name", "")}</h2>
        <p style='color: rgba(255,255,255,0.9); margin: 0.5rem 0 0 0; font-size: 1.2rem;'>
            {card.get("team") or "Free Agent"} • {card.get("position") or "—"}
        </p>
    </div>
""", unsafe_allow_html=True)

seasons = list_seasons_for_player(player_id, refresh=refresh)
if not seasons:
    st.error("No seasons found for this player.")
    st.stop()

season = st.selectbox("Select Season", options=list(reversed(seasons)))

# Season totals
with st.spinner("Loading season statistics..."):
    totals = get_player_season_totals(player_id, season, refresh=refresh)

if totals.empty:
    st.info("No season totals available for this season.")
else:
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

    # Key Stats with enhanced design
    st.markdown("### Season Overview")
    
    k1, k2, k3, k4, k5 = st.columns(5)
    
    with k1:
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        st.metric("Points Per Game", str(ppg), help="Average points scored per game")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with k2:
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        st.metric("Rebounds Per Game", str(rpg), help="Average rebounds per game")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with k3:
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        st.metric("Assists Per Game", str(apg), help="Average assists per game")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with k4:
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        st.metric("Steals Per Game", str(spg), help="Average steals per game")
        st.markdown('</div>', unsafe_allow_html=True)
    
    with k5:
        st.markdown('<div class="metric-container">', unsafe_allow_html=True)
        st.metric("Blocks Per Game", str(bpg), help="Average blocks per game")
        st.markdown('</div>', unsafe_allow_html=True)

    st.divider()

    # Detailed Stats Table with better formatting
    st.markdown("### Detailed Statistics")
    
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
    
    # Create a more visually appealing dataframe
    df_display = pd.DataFrame([display_row])
    
    # Style the dataframe
    st.dataframe(
        df_display,
        use_container_width=True,
        hide_index=True,
        column_config={
            "Season": st.column_config.TextColumn("Season", width="small"),
            "Team": st.column_config.TextColumn("Team", width="medium"),
            "GP": st.column_config.NumberColumn("Games", width="small"),
            "MP": st.column_config.TextColumn("Minutes", width="small"),
            "PPG": st.column_config.NumberColumn("PPG", width="small", format="%.1f"),
            "RPG": st.column_config.NumberColumn("RPG", width="small", format="%.1f"),
            "APG": st.column_config.NumberColumn("APG", width="small", format="%.1f"),
            "SPG": st.column_config.NumberColumn("SPG", width="small", format="%.1f"),
            "BPG": st.column_config.NumberColumn("BPG", width="small", format="%.1f"),
            "FG%": st.column_config.TextColumn("FG%", width="small"),
        }
    )

st.divider()

# Charts with enhanced styling
st.markdown("### Career Trends")
st.caption("Track performance progression throughout the player's career")

series = player_career_pts_fg(player_id, refresh=refresh)
if series.empty or "Season" not in series.columns:
    st.info("Not enough data to display career trends.")
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
            return float(row.get("PTS", 0))
        except Exception:
            return None

    s = s.copy()
    s["PPG"] = s.apply(compute_ppg, axis=1)

    # Create two side-by-side charts with better styling
    c1, c2 = st.columns(2)

    with c1:
        st.markdown('<p class="chart-title">Points Per Game by Season</p>', unsafe_allow_html=True)
        fig1, ax1 = plt.subplots(figsize=(8, 5))
        
        # Create gradient bars
        colors = plt.cm.Blues([(i / len(s)) * 0.5 + 0.5 for i in range(len(s))])
        bars = ax1.bar(s["Season"], s["PPG"].round(1), color=colors, edgecolor='#333', linewidth=1.5)
        
        ax1.set_xlabel("Season", fontsize=12, fontweight='bold')
        ax1.set_ylabel("Points Per Game", fontsize=12, fontweight='bold')
        ax1.tick_params(axis='x', rotation=45, labelsize=10)
        ax1.tick_params(axis='y', labelsize=10)
        ax1.grid(axis='y', alpha=0.3, linestyle='--')
        ax1.spines['top'].set_visible(False)
        ax1.spines['right'].set_visible(False)
        plt.tight_layout()
        
        st.pyplot(fig1, clear_figure=True)

    with c2:
        st.markdown('<p class="chart-title">Field Goal % by Season</p>', unsafe_allow_html=True)
        fig2, ax2 = plt.subplots(figsize=(8, 5))
        
        # Create line with markers
        ax2.plot(s["Season"], s["FG%"], marker="o", linewidth=2.5, 
                markersize=8, color='#667eea', markerfacecolor='#764ba2', 
                markeredgecolor='white', markeredgewidth=2)
        
        ax2.set_xlabel("Season", fontsize=12, fontweight='bold')
        ax2.set_ylabel("Field Goal %", fontsize=12, fontweight='bold')
        ax2.tick_params(axis='x', rotation=45, labelsize=10)
        ax2.tick_params(axis='y', labelsize=10)
        ax2.grid(True, alpha=0.3, linestyle='--')
        ax2.spines['top'].set_visible(False)
        ax2.spines['right'].set_visible(False)
        plt.tight_layout()
        
        st.pyplot(fig2, clear_figure=True)

# Footer
st.divider()
st.markdown("""
    <div style='text-align: center; color: #888; padding: 1rem;'>
        <p style='margin: 0;'>Data sourced from NBA Stats API</p>
    </div>
""", unsafe_allow_html=True)

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

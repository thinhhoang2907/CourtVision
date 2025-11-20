import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from courtvision.data.nba_client import (
    search_players,
    recent_seasons,
    get_player_shotchart,
)

# Page config for better styling
st.set_page_config(layout="wide")

st.title("🏀 Shot Charts & Efficiency")

# Add some styling with custom CSS
st.markdown("""
    <style>
    .stRadio > label {
        font-weight: 600;
        font-size: 16px;
        color: #1f77b4;
    }
    .plot-container {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 20px;
        border-radius: 15px;
        margin: 10px 0;
    }
    </style>
""", unsafe_allow_html=True)

# --- Global controls with better layout ---
st.markdown("### ⚙️ Settings")
control_cols = st.columns([2, 2, 1, 1])
season = control_cols[0].selectbox("📅 Season", options=recent_seasons(10))
season_type = control_cols[1].selectbox("🏆 Season Type", options=["Regular Season", "Playoffs"])
refresh = control_cols[3].button("🔄 Refresh", use_container_width=True)

st.divider()

st.markdown("### 👥 Select Players to Compare")
st.caption("Search for up to two players to visualize their shot profiles side-by-side")


# ---------- Player selection helpers ----------

def _pick_player(col, label: str, key_prefix: str):
    """
    Simple name-search-based player picker with enhanced styling.
    Returns dict {'player_id': int, 'name': str} or None.
    """
    col.markdown(f"**{label}**")
    query = col.text_input(f"🔍 Search player name", key=f"{key_prefix}_query", label_visibility="collapsed")
    query = query.strip()
    if not query:
        return None

    matches = search_players(query)
    if not matches:
        col.info("No players found.")
        return None

    options = [f"{m['full_name']} (id={m['player_id']})" for m in matches]
    idx = col.selectbox(
        f"Select player",
        options=list(range(len(options))),
        format_func=lambda i: options[i],
        key=f"{key_prefix}_select",
        label_visibility="collapsed"
    )
    text = options[idx]
    try:
        pid = int(text.split("(id=")[1].split(")")[0])
    except Exception:
        col.error("Could not parse player id.")
        return None
    name = text.split(" (id=")[0]
    return {"player_id": pid, "name": name}


# ---------- Player pickers (two players only) ----------

col_left, col_mid, col_right = st.columns([1, 0.1, 1])

with col_left:
    st.markdown("#### 🔵 Player A")
    player_a = _pick_player(st, "Player A", "A")

with col_mid:
    st.markdown("")
    st.markdown("")
    st.markdown("")
    st.markdown("### VS")

with col_right:
    st.markdown("#### 🔴 Player B")
    player_b = _pick_player(st, "Player B", "B")

if not player_a and not player_b:
    st.info("👆 Search and select at least one player to begin")
    st.stop()

players = [p for p in [player_a, player_b] if p is not None]
if len(players) == 1:
    st.warning("⚠️ You only selected one player — charts will show that player alone.")
elif len(players) > 2:
    players = players[:2]

st.divider()

# ---------- Load shot data ----------

all_shots = []
for p in players:
    with st.spinner(f"🏀 Loading shots for {p['name']}..."):
        df = get_player_shotchart(
            p["player_id"],
            season,
            season_type=season_type,
            refresh=refresh,
        )
    if df.empty:
        st.warning(f"No shot data for {p['name']} in {season} ({season_type}).")
        continue
    df = df.copy()
    df["Player"] = p["name"]
    all_shots.append(df)

if not all_shots:
    st.info("No shot data available for the selected players / season.")
    st.stop()

shots = pd.concat(all_shots, ignore_index=True)

# Minimal extra columns
if "SHOT_MADE_FLAG" in shots.columns:
    shots["Result"] = shots["SHOT_MADE_FLAG"].map({1: "Made", 0: "Miss"}).fillna("Unknown")
if "SHOT_DISTANCE" not in shots.columns:
    shots["SHOT_DISTANCE"] = None

# Calculate some stats for display
stats_data = []
for p in players:
    player_shots = shots[shots["Player"] == p["name"]]
    total_shots = len(player_shots)
    made_shots = (player_shots["SHOT_MADE_FLAG"] == 1).sum() if "SHOT_MADE_FLAG" in player_shots.columns else 0
    fg_pct = (made_shots / total_shots * 100) if total_shots > 0 else 0
    
    stats_data.append({
        "Player": p["name"],
        "Total Shots": total_shots,
        "Made": made_shots,
        "FG%": f"{fg_pct:.1f}%"
    })

# Display stats
st.markdown("### 📊 Shot Statistics")
stat_cols = st.columns(len(stats_data))
for idx, stat in enumerate(stats_data):
    with stat_cols[idx]:
        st.metric(f"**{stat['Player']}**", stat['FG%'], f"{stat['Made']}/{stat['Total Shots']}")

st.divider()

# ---------- Court helper ----------

def draw_court_lines():
    """
    Generate court line coordinates as numpy arrays for plotting.
    Returns list of (x, y) arrays for each court element.
    """
    import numpy as np
    
    lines = []
    
    # Court dimensions
    baseline_y = -47.5
    court_width = 250
    
    # ===== OUTER BOUNDARY =====
    # Baseline
    lines.append((np.array([-court_width, court_width]), np.array([baseline_y, baseline_y])))
    # Left sideline
    lines.append((np.array([-court_width, -court_width]), np.array([baseline_y, 470])))
    # Right sideline
    lines.append((np.array([court_width, court_width]), np.array([baseline_y, 470])))
    
    # ===== BACKBOARD =====
    lines.append((np.array([-30, 30]), np.array([-7.5, -7.5])))
    
    # ===== HOOP =====
    hoop_theta = np.linspace(0, 2*np.pi, 50)
    hoop_x = 7.5 * np.cos(hoop_theta)
    hoop_y = 7.5 * np.sin(hoop_theta)
    lines.append((hoop_x, hoop_y))
    
    # ===== PAINT/KEY =====
    lane_width = 80  # half width on each side
    free_throw_y = baseline_y + 190
    
    # Left lane line
    lines.append((np.array([-lane_width, -lane_width]), np.array([baseline_y, free_throw_y])))
    # Right lane line
    lines.append((np.array([lane_width, lane_width]), np.array([baseline_y, free_throw_y])))
    # Free throw line
    lines.append((np.array([-lane_width, lane_width]), np.array([free_throw_y, free_throw_y])))
    
    # ===== FREE THROW CIRCLE =====
    # Top arc (solid)
    ft_theta = np.linspace(0, np.pi, 50)
    ft_x = 60 * np.cos(ft_theta)
    ft_y = 60 * np.sin(ft_theta) + free_throw_y
    lines.append((ft_x, ft_y))
    
    # ===== RESTRICTED AREA =====
    # Small arc under basket
    restricted_theta = np.linspace(0, np.pi, 30)
    restricted_x = 40 * np.cos(restricted_theta)
    restricted_y = 40 * np.sin(restricted_theta)
    lines.append((restricted_x, restricted_y))
    
    # ===== THREE-POINT LINE =====
    # Left corner
    lines.append((np.array([-220, -220]), np.array([baseline_y, 92.5])))
    # Right corner
    lines.append((np.array([220, 220]), np.array([baseline_y, 92.5])))
    
    # Three-point arc
    corner_angle = np.arctan2(92.5, 220)
    three_theta = np.linspace(corner_angle, np.pi - corner_angle, 100)
    three_x = 237.5 * np.cos(three_theta)
    three_y = 237.5 * np.sin(three_theta)
    lines.append((three_x, three_y))
    
    return lines


def add_simplified_court(fig):
    """
    Add court lines to figure using scatter traces.
    """
    court_lines = draw_court_lines()
    
    # Find all subplot references
    axes_pairs = [("xaxis", "yaxis")]
    i = 2
    while f"xaxis{i}" in fig.layout and f"yaxis{i}" in fig.layout:
        axes_pairs.append((f"xaxis{i}", f"yaxis{i}"))
        i += 1
    
    # Add court lines to each subplot
    for idx, (xaxis_key, yaxis_key) in enumerate(axes_pairs):
        xaxis_num = "" if idx == 0 else str(idx + 1)
        yaxis_num = "" if idx == 0 else str(idx + 1)
        
        for line_x, line_y in court_lines:
            fig.add_trace(
                dict(
                    type="scatter",
                    x=line_x,
                    y=line_y,
                    mode="lines",
                    line=dict(color="#333333", width=2),  # Dark gray lines for light background
                    showlegend=False,
                    hoverinfo="skip",
                    xaxis=f"x{xaxis_num}" if xaxis_num else "x",
                    yaxis=f"y{yaxis_num}" if yaxis_num else "y",
                )
            )
    
    return fig


def apply_court_layout(fig):
    """
    Apply consistent court dimensions and aspect ratio to all subplots.
    """
    x_range = [-250, 250]
    y_range = [-52, 440]
    
    # Update all x and y axes
    fig.update_xaxes(
        range=x_range,
        showgrid=False,
        zeroline=False,
        showticklabels=False,
        title=""
    )
    fig.update_yaxes(
        range=y_range,
        scaleanchor="x",
        scaleratio=1,
        showgrid=False,
        zeroline=False,
        showticklabels=False,
        title=""
    )
    
    return fig


# ---------- Shot scatter chart ----------

st.markdown("### 🎯 Shot Chart")
st.caption("Each dot represents a shot attempt. Hover over shots to see details.")

color_mode = st.radio(
    "Color shots by:",
    options=["Player", "Make/Miss", "Shot zone"],
    horizontal=True,
)

if color_mode == "Player":
    color_col = "Player"
    color_map = {"Nikola Jokić": "#1f77b4", "Kevin Durant": "#ff7f0e"}  # Custom colors
elif color_mode == "Make/Miss" and "Result" in shots.columns:
    color_col = "Result"
    color_map = {"Made": "#2ecc71", "Miss": "#e74c3c"}  # Green for made, red for miss
else:
    color_col = "SHOT_ZONE_BASIC" if "SHOT_ZONE_BASIC" in shots.columns else "Player"
    color_map = None

# Minimal hover: player, distance, result
hover_data = {
    "Player": True,
    "SHOT_DISTANCE": True,
    "Result": True if "Result" in shots.columns else False,
    "SHOT_ZONE_BASIC": False,
    "GAME_DATE": False,
    "LOC_X": False,
    "LOC_Y": False,
}

fig_scatter = px.scatter(
    shots,
    x="LOC_X",
    y="LOC_Y",
    color=color_col,
    color_discrete_map=color_map,
    hover_data=hover_data,
    facet_col="Player" if len(players) > 1 else None,
    opacity=0.7,
)

# Update marker size and styling
fig_scatter.update_traces(marker=dict(size=8, line=dict(width=0.5, color='#333333')))

# Apply court layout and add court lines
fig_scatter = apply_court_layout(fig_scatter)
fig_scatter = add_simplified_court(fig_scatter)

fig_scatter.update_layout(
    height=650,
    margin=dict(l=10, r=10, t=50, b=10),
    legend=dict(
        orientation="h",
        yanchor="bottom",
        y=1.02,
        xanchor="center",
        x=0.5,
        font=dict(size=12, color="#333333")
    ),
    plot_bgcolor="#f0e6d2",  # Light tan court color (like real wood)
    paper_bgcolor="#ffffff",
    font=dict(color="#333333", size=12),
)

# Update subplot titles
fig_scatter.for_each_annotation(lambda a: a.update(
    text=a.text.split("=")[-1],
    font=dict(size=16, color="#333333", family="Arial Black")
))

st.plotly_chart(fig_scatter, use_container_width=True)

st.divider()

# ---------- Efficiency / Volume Heatmap ----------
st.markdown("### 🔥 Efficiency Heatmap")
st.caption("Darker areas show cold zones, brighter areas show hot zones. The court glows where players are most effective!")

metric = st.radio(
    "Heatmap metric:",
    options=["FG%", "Shot volume (FGA)"],
    horizontal=True,
)

shots_heat = shots.dropna(subset=["LOC_X", "LOC_Y"])

if shots_heat.empty:
    st.info("No valid shot locations to build a heatmap.")
else:
    # Fixed court extents
    x_min, x_max = -250, 250
    y_min, y_max = -52, 440
    bins_x = 30
    bins_y = 30

    if metric == "FG%" and "SHOT_MADE_FLAG" in shots_heat.columns:
        fig_heat = px.density_heatmap(
            shots_heat,
            x="LOC_X",
            y="LOC_Y",
            z="SHOT_MADE_FLAG",
            histfunc="avg",
            nbinsx=bins_x,
            nbinsy=bins_y,
            facet_col="Player" if len(players) > 1 else None,
            color_continuous_scale=[
                [0.0, "#1a0033"],   # Deep purple (0%)
                [0.2, "#4d0080"],   # Purple
                [0.35, "#8B00FF"],  # Violet
                [0.5, "#FF1493"],   # Deep pink
                [0.65, "#FF6347"],  # Tomato
                [0.8, "#FFD700"],   # Gold
                [1.0, "#FFFF00"],   # Bright yellow (100%)
            ],
            range_color=(0, 1),
            labels={"SHOT_MADE_FLAG": "FG%"},
        )
        color_title = "FG%"
    else:
        fig_heat = px.density_heatmap(
            shots_heat,
            x="LOC_X",
            y="LOC_Y",
            nbinsx=bins_x,
            nbinsy=bins_y,
            facet_col="Player" if len(players) > 1 else None,
            color_continuous_scale=[
                [0.0, "#0a0a0a"],   # Almost black (low)
                [0.2, "#2d1b69"],   # Dark purple
                [0.4, "#7209b7"],   # Purple
                [0.6, "#f72585"],   # Pink
                [0.8, "#ff6d00"],   # Orange
                [1.0, "#ffd60a"],   # Yellow (high)
            ],
        )
        color_title = "Shot Count"

    # Force consistent bins across court
    fig_heat.update_traces(
        xbins=dict(start=x_min, end=x_max, size=(x_max - x_min) / bins_x),
        ybins=dict(start=y_min, end=y_max, size=(y_max - y_min) / bins_y),
        zsmooth="best",
    )

    # Apply court layout and add court lines
    fig_heat = apply_court_layout(fig_heat)
    fig_heat = add_simplified_court(fig_heat)

    fig_heat.update_layout(
        height=650,
        margin=dict(l=10, r=10, t=50, b=10),
        coloraxis_colorbar=dict(
            title=dict(text=color_title, font=dict(size=14, color="white")),
            tickformat=".0%" if metric == "FG%" else None,
            tickfont=dict(color="white", size=12),
            len=0.7,
            thickness=20,
        ),
        plot_bgcolor="#000000",  # Black background like Curry chart
        paper_bgcolor="#16213e",
        font=dict(color="white", size=12),
    )

    # Update subplot titles
    fig_heat.for_each_annotation(lambda a: a.update(
        text=a.text.split("=")[-1],
        font=dict(size=16, color="white", family="Arial Black")
    ))

    st.plotly_chart(fig_heat, use_container_width=True)

# Add footer
st.divider()
st.markdown("""
    <div style='text-align: center; color: #888; padding: 20px;'>
        <p>📊 Data from NBA Stats API | Shot coordinates in 1/10 foot units</p>
        <p>💡 Tip: Use the Plotly toolbar to zoom, pan, and download charts</p>
    </div>
""", unsafe_allow_html=True)
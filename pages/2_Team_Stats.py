import streamlit as st
import pandas as pd
import time
import matplotlib.pyplot as plt
from courtvision.data.nba_client import (
	find_teams_by_name,
	get_team_roster,
	get_cached_player_stats_for_season,
	get_player_stats_for_season,
	get_player_season_series,
)

st.title("Team Stats")

team_query = st.text_input("Search team by name or abbreviation", key='team_query')
search = st.button("Search Team")

if search and not st.session_state.team_query.strip():
	st.warning("Please enter a team name or abbreviation.")

if search and st.session_state.team_query.strip():
	with st.spinner("Searching teams…"):
		matches = find_teams_by_name(st.session_state.team_query.strip())
	# store matches in session state so selection persists across reruns
	st.session_state['team_matches'] = matches
	# reset selected team key
	if 'team_select' in st.session_state:
		del st.session_state['team_select']

# If we have matches in session_state, render the team UI
matches = st.session_state.get('team_matches') if 'team_matches' in st.session_state else None
if matches is None:
	# nothing to show until the user searches
	matches = None

if matches:
	if not matches:
		st.error("No matching team found.")
	else:
		if len(matches) > 1:
			sel_options = [f"{t['full_name']} ({t.get('abbreviation','')})" for t in matches]
			sel_name = st.selectbox("Multiple matches — pick a team", sel_options, key='team_select')
			sel = next(t for t in matches if f"{t['full_name']} ({t.get('abbreviation','')})" == sel_name)
		else:
			sel = matches[0]

		st.subheader(f"{sel['full_name']} — Roster")

	# season selector (persisted)
	season = st.selectbox('Season', ['2023-24'], index=0, key='team_season')

	# roster (cached if available)
	roster = get_team_roster(sel['id'], season)
	if roster.empty:
		st.info('No roster found for this team/season.')
	else:
		# Show basic roster cols
		display_roster = roster.copy()
		# normalize column names that might be present in endpoint
		# expected: ['PLAYER', 'PLAYER_ID', 'NUM', 'POSITION', 'HEIGHT', 'WEIGHT', 'FROM_YEAR', 'TO_YEAR']
		# show subset
		show_cols = [c for c in ['PLAYER', 'PLAYER_ID', 'NUM', 'POSITION'] if c in display_roster.columns]
		display = display_roster[show_cols].copy()

		# append per-game averages from cache by default
		if 'PLAYER_ID' in display.columns:
			stats_cols = ['PTS','REB','AST','FG%','3P%','FT%','G','MP']
			for sc in stats_cols:
				display.loc[:, sc] = ''
			for i, row in display.iterrows():
				try:
					pid = int(row['PLAYER_ID'])
				except Exception:
					try:
						pid = int(float(row['PLAYER_ID']))
					except Exception:
						pid = None
				if pid is None:
					continue
				cached = get_cached_player_stats_for_season(pid, season)
				if not cached.empty:
					r = cached.iloc[0]
					# convert totals to per-game averages if needed; here we assume totals already are per-game in cached CSV or are totals — we'll default to showing the numeric fields available
					for sc in stats_cols:
						if sc in r.index:
							display.loc[i, sc] = r[sc]

		st.dataframe(display, width='stretch')

		# manual refresh button to fetch per-player stats live (user-initiated)
		if st.button('Fetch/refresh player stats for roster'):
			total = len(display)
			progress = st.progress(0)
			status_place = st.empty()
			with st.spinner('Fetching player stats (may take time)'):
				for idx, (i, row) in enumerate(display.iterrows()):
					try:
						pid_raw = row.get('PLAYER_ID') if 'PLAYER_ID' in row.index else None
						try:
							pid = int(pid_raw)
						except Exception:
							# try converting from float or string
							pid = int(float(pid_raw)) if pid_raw is not None else None
						if pid is None:
							status_place.write(f"Skipping row {i}: no PLAYER_ID")
							continue

						df = get_player_stats_for_season(pid, season)
						if df.empty:
							# try reading cache after API attempt
							df = get_cached_player_stats_for_season(pid, season)

						if not df.empty:
							r = df.iloc[0]
							for sc in ['PTS','REB','AST','FG%','3P%','FT%','G','MP']:
								if sc in r.index:
									display.at[i, sc] = r[sc]
							status_place.write(f"[{idx+1}/{total}] Fetched stats for {row.get('PLAYER', pid)} (id={pid})")
						else:
							status_place.write(f"[{idx+1}/{total}] No stats found for {row.get('PLAYER', pid)} (id={pid})")
					except Exception as e:
						status_place.write(f"[{idx+1}/{total}] Error for row {i}: {e}")
					# small delay to reduce burst rate
					time.sleep(0.5)
					progress.progress((idx+1)/total)
			st.success('Roster stats refresh complete (cached)')
			st.dataframe(display, width='stretch')

		# Basic team-level aggregates (per-game averages across roster where available)
		numeric = []
		try:
			numeric = display[[c for c in ['PTS','REB','AST','G','MP'] if c in display.columns]].apply(pd.to_numeric, errors='coerce')
			team_pts = numeric['PTS'].mean() if 'PTS' in numeric.columns else None
			cols = st.columns(3)
			cols[0].metric('Team PTS (avg roster)', f"{team_pts:.1f}" if team_pts is not None else '—')
		except Exception:
			pass

		# Simple Matplotlib plot for team PTS across seasons (placeholder requires aggregation across seasons)
		st.markdown('### Team visualizations (season trend)')
		# Build aggregated per-season averages across cached player season series
		# Collect season -> list of player PTS for that season
		season_map = {}
		if 'PLAYER_ID' in display.columns:
			for i, row in display.iterrows():
				pid = int(row['PLAYER_ID'])
				series = get_player_season_series(pid)
				if series.empty:
					continue
				for _, r in series.iterrows():
					s = str(r['Season'])
					if 'PTS' in r.index:
						season_map.setdefault(s, []).append(float(r['PTS']))

		seasons_sorted = sorted(season_map.keys(), key=lambda s: int(s[:4]))
		avg_pts = [ (sum(season_map[s]) / len(season_map[s])) if season_map.get(s) else None for s in seasons_sorted ]

		fig, ax = plt.subplots()
		if seasons_sorted:
			ax.bar(seasons_sorted, avg_pts, color='C1')
			ax.set_ylabel('Avg PTS per player')
			ax.set_title(f'{sel["full_name"]} - Avg PTS per player by season')
			plt.xticks(rotation=45)
		else:
			ax.text(0.5, 0.5, 'No aggregate data', ha='center')
		st.pyplot(fig)

		# Plotly interactive
		with st.expander('Interactive team charts (Plotly)'):
			try:
				import plotly.express as px
				dfp = pd.DataFrame({'Season': seasons_sorted, 'AvgPTS': avg_pts})
				if not dfp.empty:
					bar = px.bar(dfp, x='Season', y='AvgPTS', title=f"{sel['full_name']} - Avg PTS per player by season")
					line = px.line(dfp, x='Season', y='AvgPTS', title=f"{sel['full_name']} - Avg PTS trend", markers=True)
					st.plotly_chart(bar, width='stretch')
					st.plotly_chart(line, width='stretch')
			except Exception:
				st.info('Interactive charts unavailable')

#from nba_api.stats.static import players
#from nba_api.stats.endpoints import commonplayerinfo, playerprofilev2
import pandas as pd
from pathlib import Path
import json
import time
import logging
import datetime as dt

from nba_api.stats.static import teams as static_teams, players as static_players
from nba_api.stats.endpoints import (
        commonplayerinfo,
        playercareerstats,
        commonteamroster,
        teamdashboardbygeneralsplits,
        leaguedashplayerstats,
)

CACHE_DIR = Path("data/cache")
CACHE_DIR.mkdir(parents=True, exist_ok=True)

def _p(name):
    p = CACHE_DIR / name
    p.parent.mkdir(parents=True, exist_ok=True)
    return p

def _save_json(path, obj): path.write_text(json.dumps(obj, indent=2))
def _load_json(path): return json.loads(path.read_text())
def _save_csv(path, df): df.to_csv(path, index=False)
def _load_csv(path): return pd.read_csv(path)

# -------------------- seasons --------------------
def _current_season_str():
    today = dt.date.today()
    y = today.year if today.month >= 10 else today.year - 1
    return f"{y}-{(y+1)%100:02d}"

def recent_seasons(n=10):
    start = int(_current_season_str()[:4])
    return [f"{y}-{(y+1)%100:02d}" for y in range(start, start - n, -1)]

# -------------------- guards --------------------
# def _require_nba():
#     if not NBA_OK:
#         raise RuntimeError(
#             "nba_api failed to import. Try: pip install --upgrade nba_api\n"
#             f"Original error: {NBA_IMPORT_ERROR}"
#         )

# -------------------- teams & players --------------------
def list_all_teams():
    #_require_nba()
    ts = static_teams.get_teams()
    out = [{
        "team_id": t["id"],
        "full_name": t["full_name"],
        "abbreviation": t.get("abbreviation", ""),
        "city": t.get("city", ""),
    } for t in ts]
    return sorted(out, key=lambda x: x["full_name"])

def find_teams_by_name(query):
    q = query.lower().strip()
    return [t for t in list_all_teams() if q in t["full_name"].lower()]

def search_players(query):
    #_require_nba()
    raw = static_players.find_players_by_full_name(query or "")
    return [{"player_id": p["id"], "full_name": p["full_name"], "is_active": p.get("is_active", False)} for p in raw]

# -------------------- player cards & stats --------------------
def get_player_card(player_id, refresh=False):
    #_require_nba()
    cp = _p(f"player_info_{player_id}.json")
    if cp.exists() and not refresh:
        try: return _load_json(cp)
        except Exception: pass
    try:
        info = commonplayerinfo.CommonPlayerInfo(player_id=player_id, timeout=25).get_normalized_dict()
        row = info["CommonPlayerInfo"][0]
        card = {
            "player_id": player_id,
            "full_name": row.get("DISPLAY_FIRST_LAST") or row.get("DISPLAY_LAST_COMMA_FIRST") or f"Player {player_id}",
            "team": row.get("TEAM_NAME", "") or "",
            "position": row.get("POSITION", "") or "",
            "last_updated": int(time.time()),
        }
        _save_json(cp, card)
        return card
    except Exception:
        return {"player_id": player_id, "full_name": f"Player {player_id}", "team": "", "position": ""}

def _career_df(player_id, refresh=False):
    #_require_nba()
    cp = _p(f"player_career_{player_id}.csv")
    if cp.exists() and not refresh:
        try: return _load_csv(cp)
        except Exception: pass
    try:
        df = playercareerstats.PlayerCareerStats(player_id=player_id, timeout=30).get_data_frames()[0]
        _save_csv(cp, df)
        return df
    except Exception:
        return pd.DataFrame()

def list_seasons_for_player(player_id, refresh=False):
    df = _career_df(player_id, refresh=refresh)
    if "SEASON_ID" not in df.columns: return []
    seasons = sorted(df["SEASON_ID"].dropna().unique().tolist())
    return seasons

def player_career_pts_fg(player_id, refresh=False):
    df = _career_df(player_id, refresh=refresh)
    if df.empty: return pd.DataFrame(columns=["Season","PTS","FG%"])
    cols = [c for c in ["SEASON_ID","PTS","FG_PCT"] if c in df.columns]
    df = df[cols].rename(columns={"SEASON_ID":"Season","FG_PCT":"FG%"})
    if "FG%" in df.columns:
        df["FG%"] = (df["FG%"].astype(float) * 100).round(1)
    return df.reset_index(drop=True)

def get_player_season_totals(player_id, season_id, refresh=False):
    df = _career_df(player_id, refresh=refresh)
    if df.empty or "SEASON_ID" not in df.columns: return pd.DataFrame()
    row = df[df["SEASON_ID"] == season_id]
    if row.empty: return pd.DataFrame()
    keep = [c for c in [
        "SEASON_ID","TEAM_ABBREVIATION","GP","GS","MIN","PTS","REB","AST","STL","BLK","FG_PCT","FG3_PCT","FT_PCT","TOV","PLUS_MINUS"
    ] if c in row.columns]
    row = row[keep].rename(columns={
        "SEASON_ID": "Season",
        "TEAM_ABBREVIATION": "Team",
        "MIN": "MP",
        "FG_PCT": "FG%",
        "FG3_PCT": "3P%",
        "FT_PCT": "FT%",
        "PLUS_MINUS": "+/-",
    })
    for pct in ["FG%","3P%","FT%"]:
        if pct in row.columns:
            row[pct] = (row[pct].astype(float) * 100).round(1)
    return row.reset_index(drop=True)

# -------------------- team: roster & dashboards --------------------
def get_team_roster(team_id, season, refresh=False):
    #_require_nba()
    cp = _p(f"team_roster_{team_id}_{season}.csv")
    if cp.exists() and not refresh:
        try: return _load_csv(cp)
        except Exception: pass
    try:
        res = commonteamroster.CommonTeamRoster(team_id=team_id, season=season, timeout=30).get_data_frames()[0]
        _save_csv(cp, res)
        return res
    except Exception:
        return pd.DataFrame()

def team_players_for_dropdown(team_id, season, refresh=False):
    roster = get_team_roster(team_id, season, refresh=refresh)
    out = []
    pid_col = "PLAYER_ID" if "PLAYER_ID" in roster.columns else ("PERSON_ID" if "PERSON_ID" in roster.columns else None)
    name_col = "PLAYER" if "PLAYER" in roster.columns else ("PLAYER_NAME" if "PLAYER_NAME" in roster.columns else None)
    if pid_col and name_col:
        for _, r in roster.iterrows():
            out.append({"player_id": int(r[pid_col]), "full_name": str(r[name_col])})
    return out

def get_team_basic_stats(team_id, season, refresh=False):
    #_require_nba()
    cp = _p(f"team_basic_{team_id}_{season}.csv")
    if cp.exists() and not refresh:
        try: return _load_csv(cp)
        except Exception: pass
    try:
        dash = teamdashboardbygeneralsplits.TeamDashboardByGeneralSplits(
            team_id=team_id, season=season, timeout=30
        ).get_normalized_dict()
        frames = []
        for k, v in dash.items():
            if isinstance(v, list):
                try: frames.append(pd.DataFrame(v))
                except Exception: pass
        df = frames[0] if frames else pd.DataFrame()
        if not df.empty:
            _save_csv(cp, df)
        return df
    except Exception:
        return pd.DataFrame()

def get_team_players_season_stats(team_id, season, refresh=False):
    #_require_nba()
    cp = _p(f"team_playerstats_{team_id}_{season}.csv")
    if cp.exists() and not refresh:
        try: return _load_csv(cp)
        except Exception: pass
    try:
        df = leaguedashplayerstats.LeagueDashPlayerStats(
            season=season, team_id_nullable=team_id, per_mode_detailed="PerGame", timeout=35
        ).get_data_frames()[0]
        _save_csv(cp, df)
        return df
    except Exception:
        return pd.DataFrame()

# BASE_DIR = Path(__file__).resolve().parents[2]  # repo root
# DATA_DIR = BASE_DIR / "data"
# CACHE_DIR = DATA_DIR / "cache"
# OFFLINE_DIR = DATA_DIR / "offline"
# # Ensure directories exist and are created relative to the repository root
# CACHE_DIR.mkdir(parents=True, exist_ok=True)
# OFFLINE_DIR.mkdir(parents=True, exist_ok=True)

# logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.INFO)

# def _save_json(path: Path, obj: dict):
#     path.write_text(json.dumps(obj, indent=2), encoding="utf-8")

# def _load_json(path: Path):
#     return json.loads(path.read_text(encoding="utf-8"))

# def _cache_path_for_player_info(pid: int) -> Path:
#     return CACHE_DIR / f"player_info_{pid}.json"

# def _cache_path_for_player_totals(pid: int) -> Path:
#     return CACHE_DIR / f"player_totals_{pid}.csv"

# def find_player_basic(query: str):
#     """
#     Returns a dict with player_id, full_name, team, position (team/position may be empty if API call fails).
#     Caches basic info to speed up repeated demos.
#     """
#     matches = players.find_players_by_full_name(query)
#     if not matches:
#         return None

#     p = matches[0]
#     pid = p["id"]

#     # Try cache first
#     info_cache = _cache_path_for_player_info(pid)
#     if info_cache.exists():
#         try:
#             info = _load_json(info_cache)
#             return info
#         except Exception:
#             pass  # fall through to API

#     # API call
#     try:
#         info_raw = _with_retries(lambda: commonplayerinfo.CommonPlayerInfo(player_id=pid, timeout=10).get_normalized_dict(), max_attempts=3)
#         row = info_raw["CommonPlayerInfo"][0]
#         info = {
#             "player_id": pid,
#             "full_name": row.get("DISPLAY_FIRST_LAST", p["full_name"]),
#             "team": row.get("TEAM_NAME", "") or "",
#             "position": row.get("POSITION", "") or "",
#             "last_updated": int(time.time()),
#         }
#         _save_json(info_cache, info)
#         return info
#     except Exception as exc:
#         logger.exception("commonplayerinfo failed for pid %s: %s", pid, exc)
#         # Minimal fallback if CommonPlayerInfo fails
#         return {
#             "player_id": pid,
#             "full_name": p.get("full_name", query),
#             "team": "",
#             "position": "",
#             "last_updated": None,
#         }

# def _format_percent_cols(df: pd.DataFrame) -> pd.DataFrame:
#     for col in ["FG%", "3P%", "FT%"]:
#         if col in df.columns:
#             # coerce to float, but guard empty/NaN
#             df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0).astype(float)
#             # if values look like fractions (max <= 1), convert to percent scale
#             try:
#                 if df[col].abs().max() <= 1.01:
#                     df[col] = df[col] * 100.0
#             except Exception:
#                 # in case of all-NaN or unexpected dtypes, skip scaling
#                 pass
#             df[col] = df[col].round(1)
#     return df


# def get_player_current_season_stats(player_id: int) -> pd.DataFrame:
    
#     #Returns a one-row DataFrame for the most recent regular season totals.
#     #Flow:
#     #  1) Try API
#     #  2) If API fails, try CSV cache data/cache/player_totals_<pid>.csv
#     #  3) If cache missing and player is LeBron (2544) OR a well-known demo, try offline demo CSV.
    
#     cache_csv = _cache_path_for_player_totals(player_id)

#     # --- 1) API path
#     try:
#         prof = _with_retries(lambda: playerprofilev2.PlayerProfileV2(player_id=player_id, timeout=10).get_normalized_dict(), max_attempts=3)
#         totals = pd.DataFrame(prof.get("SeasonTotalsRegularSeason", []))
#         if totals.empty:
#             # try to fall back to a career/other endpoint before bailing to cache
#             logger.info("No SeasonTotalsRegularSeason returned for pid %s; attempting alternate endpoint", player_id)
#             try:
#                 # lazy import to avoid adding another heavy call unless needed
#                 from nba_api.stats.endpoints import playercareerstats
#                 care = _with_retries(lambda: playercareerstats.PlayerCareerStats(player_id=player_id, timeout=10).get_normalized_dict(), max_attempts=2)
#                 # playercareerstats returns season totals under 'SeasonTotalsRegularSeason' or 'SeasonTotals'
#                 alt = care.get("SeasonTotalsRegularSeason", []) or care.get("SeasonTotals", [])
#                 totals = pd.DataFrame(alt)
#             except Exception as exc2:
#                 logger.warning("playercareerstats fallback failed for pid %s: %s", player_id, exc2)

#         if totals.empty:
#             raise RuntimeError("No regular-season totals returned.")

#         # take most recent season - ensure numeric sort by season start year
#         if "SEASON_ID" in totals.columns:
#             # create numeric season start for robust sorting (e.g., '2023-24' -> 2023)
#             try:
#                 totals["SEASON_START"] = totals["SEASON_ID"].astype(str).str[:4].astype(int)
#                 totals = totals.sort_values("SEASON_START").tail(1).drop(columns=["SEASON_START"])
#             except Exception:
#                 totals = totals.sort_values("SEASON_ID").tail(1)

#         keep = ["SEASON_ID","GP","MIN","PTS","REB","AST","STL","BLK","FG_PCT","FG3_PCT","FT_PCT"]
#         keep = [c for c in keep if c in totals.columns]
#         totals = totals[keep].rename(columns={
#             "SEASON_ID":"Season","GP":"G","MIN":"MP",
#             "FG_PCT":"FG%","FG3_PCT":"3P%","FT_PCT":"FT%"
#         })
#         # convert to display percentages (guarding bad types)
#         for pct in ["FG%","3P%","FT%"]:
#             if pct in totals.columns:
#                 totals[pct] = pd.to_numeric(totals[pct], errors="coerce").fillna(0.0).astype(float)
#                 if totals[pct].abs().max() <= 1.01:
#                     totals[pct] = (totals[pct] * 100.0).round(1)
#                 else:
#                     totals[pct] = totals[pct].round(1)
#         # cache for demo reliability
#         try:
#             totals.to_csv(cache_csv, index=False)
#         except Exception:
#             logger.exception("Failed to write cache csv for pid %s", player_id)
#         return totals
#     except Exception as exc:
#         logger.exception("playerprofilev2 / alternate endpoints failed for pid %s: %s", player_id, exc)
#         # then continue to cache fallback

#     # --- 2) Cache fallback
#     if cache_csv.exists():
#         try:
#             df = pd.read_csv(cache_csv)
#             return _format_percent_cols(df)
#         except Exception:
#             pass

#     # --- 3) Offline demo fallback (only if you have a known offline file)
#     offline_csv = OFFLINE_DIR / "lebron_demo.csv"
#     if player_id in (2544,):  # LeBron's historical id; keeps demo simple
#         if offline_csv.exists():
#             try:
#                 df = pd.read_csv(offline_csv)
#                 return _format_percent_cols(df)
#             except Exception:
#                 pass

#     # If we get here, give a clear empty frame
#     return pd.DataFrame(columns=["Season","G","MP","PTS","REB","AST","STL","BLK","FG%","3P%","FT%"])

# def _with_retries(func, max_attempts=3, backoff_base=2, *args, **kwargs):
#     last_exc = None
#     for attempt in range(1, max_attempts + 1):
#         try:
#             return func(*args, **kwargs)
#         except Exception as exc:
#             last_exc = exc
#             logger.warning("Attempt %d/%d failed for %s: %s", attempt, max_attempts, getattr(func, "__name__", "call"), exc)
#             if attempt < max_attempts:
#                 time.sleep(backoff_base ** attempt)
#     # re-raise last exception to let caller handle fallback
#     raise last_exc

from nba_api.stats.static import players, teams
from nba_api.stats.endpoints import commonplayerinfo, playerprofilev2
import pandas as pd
from pathlib import Path
import json
import time
import logging

BASE_DIR = Path(__file__).resolve().parents[2]  # repo root
DATA_DIR = BASE_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
OFFLINE_DIR = DATA_DIR / "offline"
# Ensure directories exist and are created relative to the repository root
CACHE_DIR.mkdir(parents=True, exist_ok=True)
OFFLINE_DIR.mkdir(parents=True, exist_ok=True)

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def _save_json(path: Path, obj: dict):
    path.write_text(json.dumps(obj, indent=2), encoding="utf-8")

def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))

def _cache_path_for_player_info(pid: int) -> Path:
    return CACHE_DIR / f"player_info_{pid}.json"

def _cache_path_for_player_totals(pid: int) -> Path:
    return CACHE_DIR / f"player_totals_{pid}.csv"

def _cache_path_for_player_seasons(pid: int) -> Path:
    return CACHE_DIR / f"player_seasons_{pid}.json"

def _cache_path_for_team_roster(tid: int, season: str) -> Path:
    safe_season = season.replace('/', '-') if season else 'current'
    return CACHE_DIR / f"team_roster_{tid}_{safe_season}.csv"

def _is_cache_fresh(path: Path, ttl_seconds: int = CACHE_TTL_SECONDS) -> bool:
    try:
        if not path.exists():
            return False
        mtime = path.stat().st_mtime
        return (time.time() - mtime) <= ttl_seconds
    except Exception:
        return False

def find_player_basic(query: str):
    matches = players.find_players_by_full_name(query)
    if not matches:
        return None
    p = matches[0]
    pid = p["id"]
    info = commonplayerinfo.CommonPlayerInfo(player_id=pid).get_normalized_dict()["CommonPlayerInfo"][0]
    return {
        "player_id": pid,
        "full_name": info.get("DISPLAY_FIRST_LAST", p["full_name"]),
        "team": info.get("TEAM_NAME", ""),
        "position": info.get("POSITION", ""),
    }

def _convert_totals_to_per_game(df: pd.DataFrame) -> pd.DataFrame:
    """If the DataFrame appears to contain season totals (large PTS or MP), convert key totals to per-game averages by dividing by G.
    If data already looks like per-game, leave unchanged.
    """
    df = df.copy()
    if 'G' not in df.columns:
        return df
    try:
        g = pd.to_numeric(df['G'], errors='coerce')
        if g.isna().all() or (g == 0).all():
            return df

        # detect totals by PTS magnitude or MP magnitude
        is_totals = False
        if 'PTS' in df.columns:
            max_pts = pd.to_numeric(df['PTS'], errors='coerce').abs().max(skipna=True)
            if pd.notna(max_pts) and max_pts > 200:
                is_totals = True
        if not is_totals and 'MP' in df.columns:
            max_mp = pd.to_numeric(df['MP'], errors='coerce').abs().max(skipna=True)
            if pd.notna(max_mp) and max_mp > 500:
                is_totals = True

        if is_totals:
            cols_to_avg = [c for c in ['PTS','REB','AST','STL','BLK','MP'] if c in df.columns]
            for c in cols_to_avg:
                df[c] = pd.to_numeric(df[c], errors='coerce') / pd.to_numeric(df['G'], errors='coerce')
            # round sensible columns
            for c in cols_to_avg:
                df[c] = df[c].round(1)
    except Exception:
        # on any problem, return original
        return df
    return df

def find_players_by_name(query: str):
    """Return a list of basic player dicts for the given query."""
    matches = players.find_players_by_full_name(query)
    results = []
    for p in matches:
        pid = p.get('id')
        # try to load cached basic info first
        info_cache = _cache_path_for_player_info(pid)
        info = None
        if info_cache.exists():
            try:
                info = _load_json(info_cache)
            except Exception:
                info = None
        if info is None:
            # best-effort minimal info from static players list
            info = {
                'player_id': pid,
                'full_name': p.get('full_name'),
                'team': '',
                'position': '',
            }
        results.append(info)
    return results

def get_player_seasons(player_id: int):
    """Return list of seasons available for the player (strings like '2023-24'). Uses cache with TTL."""
    cache = _cache_path_for_player_seasons(player_id)
    if _is_cache_fresh(cache):
        try:
            return _load_json(cache).get('seasons', [])
        except Exception:
            pass
    # fetch from API
    seasons = []
    try:
        prof = _with_retries(lambda: playerprofilev2.PlayerProfileV2(player_id=player_id, timeout=10).get_normalized_dict(), max_attempts=3)
        totals = prof.get('SeasonTotalsRegularSeason', []) or []
        for row in totals:
            sid = row.get('SEASON_ID')
            if sid and sid not in seasons:
                seasons.append(sid)
        # sort descending by season start
        try:
            seasons = sorted(seasons, key=lambda s: int(str(s)[:4]), reverse=True)
        except Exception:
            pass
        if seasons:
            _save_json(cache, {'seasons': seasons, 'fetched_at': int(time.time())})
            return seasons
    except Exception as exc:
        logger.warning('Failed to fetch seasons for pid %s via API: %s', player_id, exc)

    # fallback: try reading cached CSV if present (maybe created previously)
    cache_csv = _cache_path_for_player_totals(player_id)
    if cache_csv.exists():
        try:
            df = pd.read_csv(cache_csv)
            if 'Season' in df.columns:
                secs = list(df['Season'].astype(str).unique())
                try:
                    secs = sorted(secs, key=lambda s: int(str(s)[:4]), reverse=True)
                except Exception:
                    pass
                if secs:
                    _save_json(cache, {'seasons': secs, 'fetched_at': int(time.time()), 'from_cache_csv': True})
                    return secs
        except Exception:
            logger.warning('Failed to read cached CSV for pid %s: %s', player_id, exc)

    # offline demo fallback for LeBron
    offline_csv = OFFLINE_DIR / 'lebron_demo.csv'
    if player_id in (2544,) and offline_csv.exists():
        try:
            df = pd.read_csv(offline_csv)
            if 'Season' in df.columns:
                secs = list(df['Season'].astype(str).unique())
                try:
                    secs = sorted(secs, key=lambda s: int(str(s)[:4]), reverse=True)
                except Exception:
                    pass
                if secs:
                    _save_json(cache, {'seasons': secs, 'fetched_at': int(time.time()), 'from_offline': True})
                    return secs
        except Exception as exc2:
            logger.warning('Failed to read offline demo for pid %s: %s', player_id, exc2)

    # nothing found
    return []

def get_player_stats_for_season(player_id: int, season: str) -> pd.DataFrame:
    """Return a one-row DataFrame for the given season (exact season string). Falls back to cache/offline like current function."""
    cache_csv = _cache_path_for_player_totals(player_id)
    # Try API with flexible matching and career fallback
    try:
        prof = _with_retries(lambda: playerprofilev2.PlayerProfileV2(player_id=player_id, timeout=10).get_normalized_dict(), max_attempts=3)
        totals_df = pd.DataFrame(prof.get('SeasonTotalsRegularSeason', []) or [])

        chosen = pd.DataFrame()
        if not totals_df.empty and 'SEASON_ID' in totals_df.columns:
            # exact match
            sel = totals_df[totals_df['SEASON_ID'] == season]
            if not sel.empty:
                chosen = sel.tail(1)
            else:
                # match by start year
                try:
                    start = str(season)[:4]
                    sel2 = totals_df[totals_df['SEASON_ID'].astype(str).str.startswith(start)]
                    if not sel2.empty:
                        chosen = sel2.tail(1)
                except Exception:
                    pass
                # contains
                if chosen.empty:
                    sel3 = totals_df[totals_df['SEASON_ID'].astype(str).str.contains(str(season))]
                    if not sel3.empty:
                        chosen = sel3.tail(1)

        # career endpoint fallback
        if chosen.empty:
            try:
                from nba_api.stats.endpoints import playercareerstats
                care = _with_retries(lambda: playercareerstats.PlayerCareerStats(player_id=player_id, timeout=10).get_normalized_dict(), max_attempts=2)
                alt = care.get('SeasonTotalsRegularSeason', []) or care.get('SeasonTotals', [])
                totals_alt = pd.DataFrame(alt)
                if not totals_alt.empty and 'SEASON_ID' in totals_alt.columns:
                    sel = totals_alt[totals_alt['SEASON_ID'] == season]
                    if not sel.empty:
                        chosen = sel.tail(1)
                    else:
                        try:
                            start = str(season)[:4]
                            sel2 = totals_alt[totals_alt['SEASON_ID'].astype(str).str.startswith(start)]
                            if not sel2.empty:
                                chosen = sel2.tail(1)
                        except Exception:
                            pass
                        if chosen.empty:
                            sel3 = totals_alt[totals_alt['SEASON_ID'].astype(str).str.contains(str(season))]
                            if not sel3.empty:
                                chosen = sel3.tail(1)
            except Exception as exc2:
                logger.info('playercareerstats fallback failed for pid %s season %s: %s', player_id, season, exc2)

        if chosen.empty:
            raise RuntimeError(f'Requested season {season} not found for player {player_id}')

        totals = chosen

        keep = [c for c in ["SEASON_ID","GP","MIN","PTS","REB","AST","STL","BLK","FG_PCT","FG3_PCT","FT_PCT"] if c in totals.columns]
        totals = totals[keep].rename(columns={"SEASON_ID":"Season","GP":"G","MIN":"MP","FG_PCT":"FG%","FG3_PCT":"3P%","FT_PCT":"FT%"})
        # convert totals to per-game averages if needed, then normalize percent columns
        totals = _convert_totals_to_per_game(totals)
        totals = _format_percent_cols(totals)
        try:
            totals.to_csv(cache_csv, index=False)
        except Exception:
            logger.exception('Failed to write cache csv for pid %s', player_id)
        return totals
    except Exception as exc:
        logger.exception('API per-season fetch failed for pid %s season %s: %s', player_id, season, exc)

    # cache fallback
    if cache_csv.exists():
        try:
            df = pd.read_csv(cache_csv)
            # try to find row matching season
            if 'Season' in df.columns:
                sel = df[df['Season'] == season]
                if not sel.empty:
                    return _format_percent_cols(sel)
        except Exception:
            pass

    # offline fallback for LeBron only
    offline_csv = OFFLINE_DIR / 'lebron_demo.csv'
    if player_id in (2544,) and offline_csv.exists():
        try:
            df = pd.read_csv(offline_csv)
            sel = df[df['Season'] == season] if 'Season' in df.columns else df
            if not sel.empty:
                return _format_percent_cols(sel)
        except Exception:
            pass

    return pd.DataFrame(columns=["Season","G","MP","PTS","REB","AST","STL","BLK","FG%","3P%","FT%"]) 

def find_teams_by_name(query: str):
    """Return a list of team dicts matching the query (both full name and abbreviation)."""
    results = []
    by_full = teams.find_teams_by_full_name(query) or []
    # some versions of nba_api expose find_team_by_abbreviation (singular)
    by_abbr = []
    try:
        by_abbr = teams.find_teams_by_abbreviation(query) or []
    except Exception:
        try:
            t = teams.find_team_by_abbreviation(query)
            by_abbr = [t] if t else []
        except Exception:
            by_abbr = []
    seen = set()
    for t in by_full + by_abbr:
        tid = t.get('id')
        if tid in seen:
            continue
        seen.add(tid)
        results.append(t)
    return results

def get_team_roster(team_id: int, season: str = '2023-24') -> pd.DataFrame:
    """Return team roster for given season; cache with TTL."""
    cache = _cache_path_for_team_roster(team_id, season)
    if _is_cache_fresh(cache):
        try:
            return pd.read_csv(cache)
        except Exception:
            pass

    try:
        from nba_api.stats.endpoints import commonteamroster
        res = _with_retries(lambda: commonteamroster.CommonTeamRoster(team_id=team_id, season=season).get_normalized_dict(), max_attempts=3)
        roster = pd.DataFrame(res.get('CommonTeamRoster', []))
        if not roster.empty:
            try:
                roster.to_csv(cache, index=False)
            except Exception:
                logger.exception('Failed to write team roster cache for team %s season %s', team_id, season)
        return roster
    except Exception as exc:
        logger.exception('Failed to fetch team roster for %s season %s: %s', team_id, season, exc)
        # fallback empty
        return pd.DataFrame()

def get_player_current_season_stats(player_id: int) -> pd.DataFrame:
    """
    Returns a one-row DataFrame for the most recent regular season totals.
    Flow:
      1) Try API
      2) If API fails, try CSV cache data/cache/player_totals_<pid>.csv
      3) If cache missing and player is LeBron (2544) OR a well-known demo, try offline demo CSV.
    """
    cache_csv = _cache_path_for_player_totals(player_id)

    # --- 1) API path
    try:
        prof = _with_retries(lambda: playerprofilev2.PlayerProfileV2(player_id=player_id, timeout=10).get_normalized_dict(), max_attempts=3)
        totals = pd.DataFrame(prof.get("SeasonTotalsRegularSeason", []))
        if totals.empty:
            # try to fall back to a career/other endpoint before bailing to cache
            logger.info("No SeasonTotalsRegularSeason returned for pid %s; attempting alternate endpoint", player_id)
            try:
                # lazy import to avoid adding another heavy call unless needed
                from nba_api.stats.endpoints import playercareerstats
                care = _with_retries(lambda: playercareerstats.PlayerCareerStats(player_id=player_id, timeout=10).get_normalized_dict(), max_attempts=2)
                # playercareerstats returns season totals under 'SeasonTotalsRegularSeason' or 'SeasonTotals'
                alt = care.get("SeasonTotalsRegularSeason", []) or care.get("SeasonTotals", [])
                totals = pd.DataFrame(alt)
            except Exception as exc2:
                logger.warning("playercareerstats fallback failed for pid %s: %s", player_id, exc2)

        if totals.empty:
            raise RuntimeError("No regular-season totals returned.")

        # take most recent season - ensure numeric sort by season start year
        if "SEASON_ID" in totals.columns:
            # create numeric season start for robust sorting (e.g., '2023-24' -> 2023)
            try:
                totals["SEASON_START"] = totals["SEASON_ID"].astype(str).str[:4].astype(int)
                totals = totals.sort_values("SEASON_START").tail(1).drop(columns=["SEASON_START"])
            except Exception:
                totals = totals.sort_values("SEASON_ID").tail(1)

        keep = ["SEASON_ID","GP","MIN","PTS","REB","AST","STL","BLK","FG_PCT","FG3_PCT","FT_PCT"]
        keep = [c for c in keep if c in totals.columns]
        totals = totals[keep].rename(columns={
            "SEASON_ID":"Season","GP":"G","MIN":"MP",
            "FG_PCT":"FG%","FG3_PCT":"3P%","FT_PCT":"FT%"
        })
        # convert to display percentages (guarding bad types)
        for pct in ["FG%","3P%","FT%"]:
            if pct in totals.columns:
                totals[pct] = pd.to_numeric(totals[pct], errors="coerce").fillna(0.0).astype(float)
                if totals[pct].abs().max() <= 1.01:
                    totals[pct] = (totals[pct] * 100.0).round(1)
                else:
                    totals[pct] = totals[pct].round(1)
        # cache for demo reliability
        try:
            totals.to_csv(cache_csv, index=False)
        except Exception:
            logger.exception("Failed to write cache csv for pid %s", player_id)
        return totals
    except Exception as exc:
        logger.exception("playerprofilev2 / alternate endpoints failed for pid %s: %s", player_id, exc)
        # then continue to cache fallback

    # --- 2) Cache fallback
    if cache_csv.exists():
        try:
            df = pd.read_csv(cache_csv)
            return _format_percent_cols(df)
        except Exception:
            pass

    # --- 3) Offline demo fallback (only if you have a known offline file)
    offline_csv = OFFLINE_DIR / "lebron_demo.csv"
    if player_id in (2544,):  # LeBron's historical id; keeps demo simple
        if offline_csv.exists():
            try:
                df = pd.read_csv(offline_csv)
                return _format_percent_cols(df)
            except Exception:
                pass

    # If we get here, give a clear empty frame
    return pd.DataFrame(columns=["Season","G","MP","PTS","REB","AST","STL","BLK","FG%","3P%","FT%"])

def _with_retries(func, max_attempts=3, backoff_base=2, *args, **kwargs):
    last_exc = None
    for attempt in range(1, max_attempts + 1):
        try:
            return func(*args, **kwargs)
        except Exception as exc:
            last_exc = exc
            logger.warning("Attempt %d/%d failed for %s: %s", attempt, max_attempts, getattr(func, "__name__", "call"), exc)
            if attempt < max_attempts:
                time.sleep(backoff_base ** attempt)
    # re-raise last exception to let caller handle fallback
    raise last_exc

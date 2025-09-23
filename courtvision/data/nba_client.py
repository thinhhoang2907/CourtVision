from nba_api.stats.static import players
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

def find_player_basic(query: str):
    """
    Returns a dict with player_id, full_name, team, position (team/position may be empty if API call fails).
    Caches basic info to speed up repeated demos.
    """
    matches = players.find_players_by_full_name(query)
    if not matches:
        return None

    p = matches[0]
    pid = p["id"]

    # Try cache first
    info_cache = _cache_path_for_player_info(pid)
    if info_cache.exists():
        try:
            info = _load_json(info_cache)
            return info
        except Exception:
            pass  # fall through to API

    # API call
    try:
        info_raw = _with_retries(lambda: commonplayerinfo.CommonPlayerInfo(player_id=pid, timeout=10).get_normalized_dict(), max_attempts=3)
        row = info_raw["CommonPlayerInfo"][0]
        info = {
            "player_id": pid,
            "full_name": row.get("DISPLAY_FIRST_LAST", p["full_name"]),
            "team": row.get("TEAM_NAME", "") or "",
            "position": row.get("POSITION", "") or "",
            "last_updated": int(time.time()),
        }
        _save_json(info_cache, info)
        return info
    except Exception as exc:
        logger.exception("commonplayerinfo failed for pid %s: %s", pid, exc)
        # Minimal fallback if CommonPlayerInfo fails
        return {
            "player_id": pid,
            "full_name": p.get("full_name", query),
            "team": "",
            "position": "",
            "last_updated": None,
        }

def _format_percent_cols(df: pd.DataFrame) -> pd.DataFrame:
    for col in ["FG%", "3P%", "FT%"]:
        if col in df.columns:
            # coerce to float, but guard empty/NaN
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0).astype(float)
            # if values look like fractions (max <= 1), convert to percent scale
            try:
                if df[col].abs().max() <= 1.01:
                    df[col] = df[col] * 100.0
            except Exception:
                # in case of all-NaN or unexpected dtypes, skip scaling
                pass
            df[col] = df[col].round(1)
    return df

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

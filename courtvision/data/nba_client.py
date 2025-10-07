from nba_api.stats.static import players, teams
from nba_api.stats.endpoints import commonplayerinfo, playerprofilev2
import pandas as pd

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
    # season totals table; pick last season row as “current”
    prof = playerprofilev2.PlayerProfileV2(player_id=player_id).get_normalized_dict()
    totals = pd.DataFrame(prof["SeasonTotalsRegularSeason"])
    if totals.empty:
        return pd.DataFrame()
    # take most recent season
    totals = totals.sort_values("SEASON_ID").tail(1)
    keep = ["SEASON_ID","GP","MIN","PTS","REB","AST","STL","BLK","FG_PCT","FG3_PCT","FT_PCT"]
    return totals[keep].rename(columns={
        "SEASON_ID":"Season","GP":"G","MIN":"MP",
        "PTS":"PTS","REB":"REB","AST":"AST","STL":"STL","BLK":"BLK",
        "FG_PCT":"FG%","FG3_PCT":"3P%","FT_PCT":"FT%"
    })

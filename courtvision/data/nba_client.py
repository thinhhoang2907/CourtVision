from nba_api.stats.static import players
from nba_api.stats.endpoints import commonplayerinfo, playerprofilev2
import pandas as pd

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

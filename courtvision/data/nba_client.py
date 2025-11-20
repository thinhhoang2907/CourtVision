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
        leaguedashteamstats,
        teamyearbyyearstats,
        teamgamelog,
        leaguegamefinder,
        shotchartdetail,

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
    if df.empty: return pd.DataFrame(columns=["Season","PTS","FG%","GP"])
    # include GP if available so callers can compute per-game values
    cols = [c for c in ["SEASON_ID","PTS","FG_PCT","GP"] if c in df.columns]
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
    cp = _p(f"team_basic_{team_id}_{season}.csv")
    if cp.exists() and not refresh:
        try:
            return _load_csv(cp)
        except Exception:
            pass

    try:
        dash = teamdashboardbygeneralsplits.TeamDashboardByGeneralSplits(
            team_id=team_id,
            season=season,
            season_type_all_star="Regular Season",     # ensure REGULAR SEASON
            per_mode_detailed="PerGame",               # per-game not required, but fine
            timeout=30
        ).get_normalized_dict()

        # Prefer the 'OverallTeamDashboard' key explicitly
        df = pd.DataFrame()
        if isinstance(dash, dict):
            if "OverallTeamDashboard" in dash and isinstance(dash["OverallTeamDashboard"], list):
                df = pd.DataFrame(dash["OverallTeamDashboard"])

        # Fallback (rare): search by name containing "Overall"
        if df.empty:
            for k, v in dash.items():
                if "overall" in str(k).lower() and isinstance(v, list):
                    try:
                        cand = pd.DataFrame(v)
                        if not cand.empty:
                            df = cand
                            break
                    except Exception:
                        pass

        # Final fallback: first list-like
        if df.empty:
            for v in dash.values():
                if isinstance(v, list):
                    try:
                        cand = pd.DataFrame(v)
                        if not cand.empty:
                            df = cand
                            break
                    except Exception:
                        pass

        if not df.empty:
            _save_csv(cp, df)
        return df

    except Exception:
        return pd.DataFrame()
    
def get_team_adv_summary(team_id, season, refresh=False):
    """
    Season-to-date REGULAR SEASON summary for one team.
    Returns a 1-row DataFrame with W, L, W_PCT, OFF_RATING, DEF_RATING, NET_RATING (and more).
    """
    cp = _p(f"team_adv_{team_id}_{season}.csv")
    if cp.exists() and not refresh:
        try:
            return _load_csv(cp)
        except Exception:
            pass

    try:
        df_all = leaguedashteamstats.LeagueDashTeamStats(
            season=season,
            season_type_all_star="Regular Season",
            measure_type_detailed_defense="Advanced",  # <-- gives Off/Def/Net Rating
            per_mode_detailed="PerGame",               # OK for counts; ratings are unaffected
            timeout=35
        ).get_data_frames()[0]

        # Filter for just this team
        row = df_all[df_all["TEAM_ID"] == team_id].copy()
        if row.empty:
            # Very rare: fall back to name match
            # (Use your static teams list to find the official name/abbrev if desired)
            return pd.DataFrame()

        # Cache the single-row frame
        _save_csv(cp, row)
        return row.reset_index(drop=True)

    except Exception:
        return pd.DataFrame()

def _season_key_to_start_year(season_str):
    # "2018-19" -> 2018
    return int(str(season_str)[:4])

def get_team_record_from_yearbyyear(team_id, season, refresh=False):
    """
    Reliable historical record. Returns DataFrame with columns:
    ['SEASON_ID','W','L','W_PCT'] for the requested season.
    """
    year = _season_key_to_start_year(season)
    cp = _p(f"team_yby_{team_id}.csv")
    if cp.exists() and not refresh:
        try:
            df_all = _load_csv(cp)
        except Exception:
            df_all = None
    else:
        df_all = None

    if df_all is None:
        try:
            df_all = teamyearbyyearstats.TeamYearByYearStats(team_id=team_id, timeout=35).get_data_frames()[0]
            _save_csv(cp, df_all)
        except Exception:
            return pd.DataFrame()

    # Normalize season label to start year for matching
    # TeamYearByYearStats typically has 'YEAR' like '2018-19' or numeric start year; capture both
    if "YEAR" in df_all.columns:
        # Keep both YEAR (e.g., '2018-19') and a derived YEAR_START (2018)
        tmp = df_all.copy()
        # Some seasons are like '2018-19', some are '2018'; handle robustly
        def _start(x):
            s = str(x)
            try:
                return int(s[:4])
            except Exception:
                return None
        tmp["YEAR_START"] = tmp["YEAR"].apply(_start)
    else:
        # older schema fallback
        tmp = df_all.copy()
        tmp["YEAR_START"] = tmp["SEASON_ID"].apply(lambda x: int(str(x)[:4])) if "SEASON_ID" in tmp.columns else None

    row = tmp[tmp["YEAR_START"] == year]
    if row.empty:
        return pd.DataFrame()

    # standardize columns
    out = pd.DataFrame([{
        "SEASON_ID": season,
        "W": int(row.iloc[0]["WINS"] if "WINS" in row.columns else row.iloc[0].get("W", 0)),
        "L": int(row.iloc[0]["LOSSES"] if "LOSSES" in row.columns else row.iloc[0].get("L", 0)),
        "W_PCT": float(row.iloc[0]["WIN_PCT"] if "WIN_PCT" in row.columns else row.iloc[0].get("W_PCT", 0.0)),
    }])
    return out


def get_team_ratings_from_advanced(team_id, season, refresh=False):
    """
    Season aggregate advanced ratings. Returns 1-row DF with:
    ['OFF_RATING','DEF_RATING','NET_RATING'] (or E_* variants).
    """
    cp = _p(f"team_adv_{team_id}_{season}.csv")
    if cp.exists() and not refresh:
        try:
            return _load_csv(cp)
        except Exception:
            pass
    try:
        df_all = leaguedashteamstats.LeagueDashTeamStats(
            season=season,
            season_type_all_star="Regular Season",
            measure_type_detailed_defense="Advanced",
            per_mode_detailed="PerGame",
            timeout=35
        ).get_data_frames()[0]

        row = df_all[df_all["TEAM_ID"] == team_id].copy()
        if row.empty:
            return pd.DataFrame()

        _save_csv(cp, row)
        return row.reset_index(drop=True)
    except Exception:
        return pd.DataFrame()


def get_team_record_and_ratings(team_id, season, refresh=False):
    """
    Single source of truth for Team page KPIs.
    Merges:
      - Record from TeamYearByYearStats (reliable historically)
      - Off/Def/Net from LeagueDashTeamStats Advanced
    Returns 1-row DF with W, L, W_PCT, OFF_RATING, DEF_RATING, NET_RATING.
    """
    rec = get_team_record_from_yearbyyear(team_id, season, refresh=refresh)
    adv = get_team_ratings_from_advanced(team_id, season, refresh=refresh)

    # Prepare ratings with alias handling
    OFF = DEF = NET = None
    if not adv.empty:
        def _g(df, *names):
            for n in names:
                if n in df.columns:
                    return float(df[n].iloc[0])
            return None
        OFF = _g(adv, "OFF_RATING", "E_OFF_RATING")
        DEF = _g(adv, "DEF_RATING", "E_DEF_RATING")
        NET = _g(adv, "NET_RATING", "E_NET_RATING")
        if NET is None and OFF is not None and DEF is not None:
            NET = OFF - DEF

    # If record missing, return just ratings (or empty)
    if rec.empty:
        if OFF is None and DEF is None and NET is None:
            return pd.DataFrame()
        return pd.DataFrame([{
            "SEASON_ID": season, "W": None, "L": None, "W_PCT": None,
            "OFF_RATING": OFF or 0.0, "DEF_RATING": DEF or 0.0, "NET_RATING": NET or 0.0
        }])

    # Merge into one row
    out = rec.copy()
    out["OFF_RATING"] = OFF or 0.0
    out["DEF_RATING"] = DEF or 0.0
    out["NET_RATING"] = NET or (OFF - DEF if (OFF is not None and DEF is not None) else 0.0)
    return out.reset_index(drop=True)

    # #_require_nba()
    # cp = _p(f"team_basic_{team_id}_{season}.csv")
    # if cp.exists() and not refresh:
    #     try: return _load_csv(cp)
    #     except Exception: pass
    # try:
    #     dash = teamdashboardbygeneralsplits.TeamDashboardByGeneralSplits(
    #         team_id=team_id, season=season, timeout=30
    #     ).get_normalized_dict()
    #     frames = []
    #     for k, v in dash.items():
    #         if isinstance(v, list):
    #             try:
    #                 frames.append(pd.DataFrame(v))
    #             except Exception:
    #                 pass

    #     # Prefer the frame that contains season-level W/L (overall team totals)
    #     df = pd.DataFrame()
    #     for f in frames:
    #         if not f.empty and ("W" in f.columns or "W_PCT" in f.columns) and ("L" in f.columns):
    #             df = f
    #             break
    #     # fallback to first frame if we couldn't find the season-level one
    #     if df.empty and frames:
    #         df = frames[0]
    #     if not df.empty:
    #         _save_csv(cp, df)
    #     return df
    # except Exception:
    #     return pd.DataFrame()

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
    

def get_player_season_row(player_id, season, refresh=False):
    """Return 1-row DF of a player's season totals (min, FGA, FTA, TOV, PTS, etc.)."""
    df = _career_df(player_id, refresh=refresh)
    if df.empty or "SEASON_ID" not in df.columns:
        return pd.DataFrame()
    row = df[df["SEASON_ID"] == season]
    return row.reset_index(drop=True)

def get_team_season_base_totals(team_id, season, refresh=False):
    """
    Team season totals we need for Usage Rate denominator.
    Pull from LeagueDashTeamStats (Base) for the whole REGULAR SEASON.
    """
    cp = _p(f"team_base_totals_{team_id}_{season}.csv")
    if cp.exists() and not refresh:
        try: return _load_csv(cp)
        except Exception: pass
    try:
        df = leaguedashteamstats.LeagueDashTeamStats(
            season=season,
            season_type_all_star="Regular Season",
            measure_type_detailed_defense="Base",
            per_mode_detailed="Totals",   # IMPORTANT: totals, not per-game
            timeout=35
        ).get_data_frames()[0]
        row = df[df["TEAM_ID"] == team_id].copy()
        if not row.empty:
            _save_csv(cp, row)
            return row.reset_index(drop=True)
    except Exception:
        pass
    return pd.DataFrame()

def compute_usage_rate(player_row, team_row):
    """
    USG% = 100 * ((FGA + 0.44*FTA + TOV) * (Team Minutes/5)) / (Minutes * (Team FGA + 0.44*Team FTA + Team TOV))
    Inputs are single-row DFs for player and team (season totals).
    Returns float or None.
    """
    if player_row.empty or team_row.empty: return None
    pr = player_row.iloc[0]; tr = team_row.iloc[0]

    # Player stats
    MP  = float(pr.get("MIN", 0) or 0)
    FGA = float(pr.get("FGA", 0) or 0)
    FTA = float(pr.get("FTA", 0) or 0)
    TOV = float(pr.get("TOV", 0) or 0)

    # Team totals
    TFGA = float(tr.get("FGA", 0) or 0)
    TFTA = float(tr.get("FTA", 0) or 0)
    TTOV = float(tr.get("TOV", 0) or 0)
    # Team minutes = 48 * games * 5 (NBA regulation minutes). 'GP' is games played.
    TGP  = float(tr.get("GP", 0) or 0)
    TMIN = 48.0 * TGP * 5.0

    denom = MP * (TFGA + 0.44 * TFTA + TTOV)
    if denom <= 0: return None
    return 100.0 * ((FGA + 0.44 * FTA + TOV) * (TMIN / 5.0)) / denom

def compute_true_shooting_pct(player_row):
    """TS% = PTS / (2*(FGA + 0.44*FTA))"""
    if player_row.empty: return None
    pr = player_row.iloc[0]
    PTS = float(pr.get("PTS", 0) or 0)
    FGA = float(pr.get("FGA", 0) or 0)
    FTA = float(pr.get("FTA", 0) or 0)
    denom = 2.0 * (FGA + 0.44 * FTA)
    if denom <= 0: return None
    return 100.0 * (PTS / denom)

def compute_player_PER(player_row, team_row, season, refresh=False):
    """
    Hollinger PER based on Basketball-Reference formula:
      1) Compute uPER with team & league constants,
      2) Adjust for pace (lgPace / tmPace),
      3) Normalize to PER (league avg = 15) using league-average uPER (minutes-weighted).
    Returns PER (float) or None.
    """
    if player_row.empty or team_row.empty:
        return None

    consts = _league_constants(season, refresh=refresh)
    if consts is None:
        return None

    # Team ratios needed in uPER (tmAST/tmFG)
    tmFG  = float(team_row.get("FGM", team_row.get("FG", 0)).iloc[0] if "FGM" in team_row.columns or "FG" in team_row.columns else 0.0)
    tmAST = float(team_row.get("AST", pd.Series([0])).iloc[0] or 0.0)

    # Pull player totals
    pr = player_row.iloc[0]
    def g(name, alt=None):
        for k in [name, alt] if alt else [name]:
            if k in player_row.columns:
                try: return float(pr[k] or 0.0)
                except Exception: return 0.0
        return 0.0

    MIN = g("MIN")
    if MIN <= 0: return None

    FG   = g("FGM","FG")
    FGA  = g("FGA")
    _3P  = g("FG3M","3PM")
    FT   = g("FTM","FT")
    FTA  = g("FTA")
    AST  = g("AST")
    ORB  = g("OREB","OREB_TOT")
    TRB  = g("REB","TRB")
    STL  = g("STL")
    BLK  = g("BLK")
    TOV  = g("TOV","TO")
    PF   = g("PF")
    PTS  = g("PTS")

    factor = consts["factor"]; VOP = consts["VOP"]; DRBP = consts["DRBP"]
    lgFT = consts["lgFT"]; lgFTA = consts["lgFTA"]; lgFG = consts["lgFG"]; lgAST = consts["lgAST"]; lgPF = consts["lgPF"]

    # uPER (BBR/Hollinger form, per minute)
    # See: Wikipedia "Calculation" section reproducing BBR formula. :contentReference[oaicite:2]{index=2}
    try:
        tmAST_over_tmFG = (tmAST / max(tmFG, 1e-9)) if tmFG else 0.0
        uPER_num = (
            _3P
            + (2.0/3.0) * AST
            + FG * (2.0 - factor * tmAST_over_tmFG)
            + 0.5 * FT * (2.0 - (1.0/3.0) * tmAST_over_tmFG)
            - VOP * TOV
            - VOP * DRBP * (FGA - FG)
            - VOP * 0.44 * (0.44 + 0.56 * DRBP) * (FTA - FT)
            + VOP * (1 - DRBP) * (TRB - ORB)
            + VOP * DRBP * ORB
            + VOP * STL
            + VOP * DRBP * BLK
            - PF * ((lgFT / max(lgPF,1e-9)) - 0.44 * (consts["lgFTA"]/max(lgPF,1e-9)) * VOP)
        )
        uPER = (1.0 / MIN) * uPER_num
    except Exception:
        return None

    # Pace adjust: PER' = uPER * (lgPace / tmPace)
    tm_id = int(team_row.get("TEAM_ID", pd.Series([None])).iloc[0] or 0)
    tmPace = team_pace(tm_id, season, refresh=refresh)
    lgPace = league_pace(season, refresh=refresh)
    if not tmPace or not lgPace:
        return None
    per_pace = uPER * (lgPace / tmPace)

    # League-average uPER (minutes-weighted) for normalization
    lguPER = league_average_uPER(season, refresh=refresh)
    if not lguPER:
        return None

    PER = per_pace * (15.0 / lguPER)
    return float(PER)

def league_average_uPER(season, refresh=False):
    """
    Compute league-average uPER as a minutes-weighted mean of player uPER for the season.
    Uses team-level ratios for tmAST/tmFG mapped to each player’s team.
    Cached to avoid recomputation.
    """
    cp = _p(f"league_avg_uPER_{season}.json")
    if cp.exists() and not refresh:
        try:
            return float(_load_json(cp)["lguPER"])
        except Exception:
            pass

    # Pull player totals league-wide
    try:
        p = leaguedashplayerstats.LeagueDashPlayerStats(
            season=season,
            season_type_all_star="Regular Season",
            per_mode_detailed="Totals",
            timeout=45
        ).get_data_frames()[0]
    except Exception:
        return None
    if p.empty: return None

    # Build team totals map (for tmAST/tmFG per team)
    team_totals = leaguedashteamstats.LeagueDashTeamStats(
        season=season, season_type_all_star="Regular Season",
        measure_type_detailed_defense="Base", per_mode_detailed="Totals",
        timeout=35
    ).get_data_frames()[0]
    team_map = {int(r["TEAM_ID"]): r for _, r in team_totals.iterrows()}

    consts = _league_constants(season, refresh=refresh)
    if consts is None: return None
    factor = consts["factor"]; VOP = consts["VOP"]; DRBP = consts["DRBP"]
    lgFT = consts["lgFT"]; lgFTA = consts["lgFTA"]; lgFG = consts["lgFG"]; lgAST = consts["lgAST"]; lgPF = consts["lgPF"]

    # Compute uPER per player (minutes > 0)
    def uper_row(r):
        MIN = float(r.get("MIN", 0) or 0)
        if MIN <= 0: return 0.0, 0.0
        TEAM_ID = int(r.get("TEAM_ID", 0) or 0)
        t = team_map.get(TEAM_ID, {})
        tmFG  = float(t.get("FGM", t.get("FG", 0)) or 0.0)
        tmAST = float(t.get("AST", 0) or 0.0)
        tmAST_over_tmFG = (tmAST / tmFG) if tmFG else 0.0

        FG   = float(r.get("FGM", r.get("FG", 0)) or 0.0)
        FGA  = float(r.get("FGA", 0) or 0.0)
        _3P  = float(r.get("FG3M", 0) or 0.0)
        FT   = float(r.get("FTM", 0) or 0.0)
        FTA  = float(r.get("FTA", 0) or 0.0)
        AST  = float(r.get("AST", 0) or 0.0)
        ORB  = float(r.get("OREB", 0) or 0.0)
        TRB  = float(r.get("REB", 0) or 0.0)
        STL  = float(r.get("STL", 0) or 0.0)
        BLK  = float(r.get("BLK", 0) or 0.0)
        TOV  = float(r.get("TOV", r.get("TO", 0)) or 0.0)
        PF   = float(r.get("PF", 0) or 0.0)

        uPER_num = (
            _3P + (2.0/3.0)*AST
            + FG * (2.0 - factor * tmAST_over_tmFG)
            + 0.5 * FT * (2.0 - (1.0/3.0) * tmAST_over_tmFG)
            - VOP*TOV
            - VOP*DRBP*(FGA - FG)
            - VOP*0.44*(0.44 + 0.56*DRBP)*(FTA - FT)
            + VOP*(1-DRBP)*(TRB - ORB)
            + VOP*DRBP*ORB
            + VOP*STL
            + VOP*DRBP*BLK
            - PF * ((lgFT/max(lgPF,1e-9)) - 0.44*(lgFTA/max(lgPF,1e-9))*VOP)
        )
        return (uPER_num / MIN), MIN

    # minutes-weighted average
    total_uPER_x_min = 0.0
    total_min = 0.0
    for _, r in p.iterrows():
        u, m = uper_row(r)
        total_uPER_x_min += u * m
        total_min += m
    lguPER = (total_uPER_x_min / total_min) if total_min > 0 else None
    if lguPER:
        _save_json(cp, {"lguPER": lguPER})
    return lguPER


def get_team_head_to_head(team_id_a, team_id_b, season, refresh=False):
    """
    Return small dict with head-to-head W-L for 'season' between team A and B using TeamGameLog.
    """
    def _one(team_id):
        cp = _p(f"h2h_{team_id}_{season}.csv")
        if cp.exists() and not refresh:
            try: return _load_csv(cp)
            except Exception: pass
        try:
            df = teamgamelog.TeamGameLog(team_id=team_id, season=season, season_type_all_star="Regular Season", timeout=30).get_data_frames()[0]
            _save_csv(cp, df)
            return df
        except Exception:
            return pd.DataFrame()

    a = _one(team_id_a); b = _one(team_id_b)
    if a.empty or b.empty:
        return {"A_wins": 0, "B_wins": 0, "games": 0}

    # Each row has 'MATCHUP' like "LAL vs BOS" or "LAL @ BOS", and 'WL' column
    def _vs(df, my_abbrev, opp_abbrev):
        m = df[df["MATCHUP"].str.contains(opp_abbrev, na=False)]
        wins = int((m["WL"] == "W").sum())
        losses = int((m["WL"] == "L").sum())
        return wins, losses, len(m)

    # Get abbreviations from your team list (already in your file)
    all_teams = list_all_teams()
    ta = next(t for t in all_teams if t["team_id"] == team_id_a)
    tb = next(t for t in all_teams if t["team_id"] == team_id_b)
    a_abbr, b_abbr = ta["abbreviation"], tb["abbreviation"]

    a_w, a_l, a_g = _vs(a, a_abbr, b_abbr)
    b_w, b_l, b_g = _vs(b, b_abbr, a_abbr)

    # Sanity combine (should match both ways)
    A_wins = a_w
    B_wins = b_w
    games  = min(a_g, b_g)
    return {"A_wins": A_wins, "B_wins": B_wins, "games": games}

#new head-to-head function
def _team_gamelog(team_id, season, refresh=False, season_type="Regular Season"):
    cp = _p(f"teamgamelog_{team_id}_{season}_{season_type.replace(' ','_')}.csv")
    if cp.exists() and not refresh:
        try:
            df = _load_csv(cp)
        except Exception:
            df = None
    else:
        df = None

    if df is None:
        try:
            df = teamgamelog.TeamGameLog(
                team_id=team_id,
                season=season,
                season_type_all_star=season_type,
                timeout=30
            ).get_data_frames()[0]
            _save_csv(cp, df)
        except Exception:
            return pd.DataFrame()

    # Normalize critical columns
    if "GAME_ID" in df.columns:
        df["GAME_ID"] = df["GAME_ID"].astype(str)         # <- KEY: force same dtype
    if "GAME_DATE" in df.columns:
        # keep original string, but store a parsed helper for sorting
        try:
            df["_GAME_DATE_DT"] = pd.to_datetime(df["GAME_DATE"])
        except Exception:
            df["_GAME_DATE_DT"] = pd.NaT
    return df

def get_team_h2h_games(team_id_a, team_id_b, season, refresh=False, season_type="Regular Season"):
    """
    Reliable head-to-head via LeagueGameFinder.
    Returns (summary, games_df)
      summary: {"A_wins": int, "B_wins": int, "games": int}
      games_df: columns [GAME_DATE, GAME_ID, PTS_A, PTS_B, MATCHUP_A] newest→oldest
    """
    def _finder(team_id, vs_id, cache_tag):
        cp = _p(f"h2h_finder_{cache_tag}_{team_id}_vs_{vs_id}_{season}_{season_type.replace(' ','_')}.csv")
        if cp.exists() and not refresh:
            try:
                return _load_csv(cp)
            except Exception:
                pass
        try:
            df = leaguegamefinder.LeagueGameFinder(
                team_id_nullable=team_id,
                vs_team_id_nullable=vs_id,
                season_nullable=season,
                season_type_nullable=season_type,
                timeout=35
            ).get_data_frames()[0]
            _save_csv(cp, df)
            return df
        except Exception:
            return pd.DataFrame()

    # Fetch “A vs B” and “B vs A”
    a = _finder(team_id_a, team_id_b, "A")
    b = _finder(team_id_b, team_id_a, "B")

    if a.empty or b.empty:
        return {"A_wins": 0, "B_wins": 0, "games": 0}, pd.DataFrame()

    # Normalize and select only what we need
    for df in (a, b):
        if "GAME_ID" in df.columns:
            df["GAME_ID"] = df["GAME_ID"].astype(str)

    keep_a = ["GAME_ID", "GAME_DATE", "PTS", "WL", "MATCHUP"]
    keep_b = ["GAME_ID", "PTS"]
    for col in keep_a:
        if col not in a.columns:
            a[col] = pd.NA
    for col in keep_b:
        if col not in b.columns:
            b[col] = pd.NA

    a_small = a[keep_a].rename(columns={"PTS": "PTS_A", "WL": "WL_A", "MATCHUP": "MATCHUP_A"})
    b_small = b[keep_b].rename(columns={"PTS": "PTS_B"})

    m = a_small.merge(b_small, on="GAME_ID", how="inner")
    if m.empty:
        return {"A_wins": 0, "B_wins": 0, "games": 0}, pd.DataFrame()

    # Sort newest → oldest by date (robust to different formats)
    try:
        m["_DT"] = pd.to_datetime(m["GAME_DATE"])
    except Exception:
        m["_DT"] = pd.NaT
    m = m.sort_values("_DT", ascending=False).reset_index(drop=True)

    # Wins/losses — prefer WL_A, fallback to comparing points
    a_wins = int((m["WL_A"] == "W").sum())
    if a_wins == 0:
        a_wins = int((m["PTS_A"] > m["PTS_B"]).sum())
    b_wins = len(m) - a_wins

    summary = {"A_wins": a_wins, "B_wins": b_wins, "games": len(m)}
    games_df = m[["GAME_DATE", "GAME_ID", "PTS_A", "PTS_B", "MATCHUP_A"]].copy()
    return summary, games_df

# Calculating the PER

def _league_team_totals(season, refresh=False):
    """
    League totals by summing team totals (Regular Season).
    Returns one-row DataFrame with FG, FGA, 3PM, FT, FTA, AST, ORB, DRB, REB, TOV, PF, PTS, GP.
    """
    cp = _p(f"league_team_totals_{season}.csv")
    if cp.exists() and not refresh:
        try: return _load_csv(cp)
        except Exception: pass
    try:
        df = leaguedashteamstats.LeagueDashTeamStats(
            season=season,
            season_type_all_star="Regular Season",
            measure_type_detailed_defense="Base",
            per_mode_detailed="Totals",
            timeout=35
        ).get_data_frames()[0]
        # Sum across all teams
        cols = ["FGM","FGA","FG3M","FTM","FTA","AST","OREB","DREB","REB","TOV","PF","PTS","GP"]
        agg = df[cols].sum(numeric_only=True).to_frame().T
        _save_csv(cp, agg)
        return agg
    except Exception:
        return pd.DataFrame()

def _league_advanced(season, refresh=False):
    """
    League advanced -> use team 'Advanced' to compute league pace (minutes-weighted).
    """
    cp = _p(f"league_team_adv_{season}.csv")
    if cp.exists() and not refresh:
        try: return _load_csv(cp)
        except Exception: pass
    try:
        adv = leaguedashteamstats.LeagueDashTeamStats(
            season=season,
            season_type_all_star="Regular Season",
            measure_type_detailed_defense="Advanced",
            per_mode_detailed="PerGame",
            timeout=35
        ).get_data_frames()[0]
        _save_csv(cp, adv)
        return adv
    except Exception:
        return pd.DataFrame()

def _team_advanced_row(team_id, season, refresh=False):
    adv = _league_advanced(season, refresh=refresh)
    if adv.empty: return pd.Series(dtype=float)
    row = adv[adv["TEAM_ID"] == team_id]
    return row.iloc[0] if not row.empty else pd.Series(dtype=float)

def league_pace(season, refresh=False):
    """
    Weighted league pace using team PACE weighted by GP.
    """
    adv = _league_advanced(season, refresh=refresh)
    if adv.empty: return None
    # weight by games played (GP) if present; else simple mean
    if "GP" in adv.columns and "PACE" in adv.columns:
        num = (adv["PACE"].astype(float) * adv["GP"].astype(float)).sum()
        den = adv["GP"].astype(float).sum()
        return float(num/den) if den else None
    return float(adv["PACE"].astype(float).mean()) if "PACE" in adv.columns else None

def team_pace(team_id, season, refresh=False):
    row = _team_advanced_row(team_id, season, refresh=refresh)
    try:
        return float(row["PACE"])
    except Exception:
        return None

def _league_constants(season, refresh=False):
    """
    Compute factor, VOP, DRBP from league totals (Hollinger/BBR).
    Returns dict { 'factor', 'VOP', 'DRBP', 'lgFT','lgFTA','lgFG','lgAST','lgTRB','lgORB','lgPTS','lgPF' }
    """
    lg = _league_team_totals(season, refresh=refresh)
    if lg.empty: return None
    lgFT  = float(lg["FTM"].iloc[0])
    lgFTA = float(lg["FTA"].iloc[0])
    lgFG  = float(lg["FGM"].iloc[0])
    lgAST = float(lg["AST"].iloc[0])
    lgTRB = float(lg["REB"].iloc[0])
    lgORB = float(lg["OREB"].iloc[0])
    lgPF  = float(lg["PF"].iloc[0])
    lgPTS = float(lg["PTS"].iloc[0])
    lgFGA = float(lg["FGA"].iloc[0])
    # Hollinger constants
    # factor = 2/3 - [0.5 * (lgAST/lgFG)] / [2 * (lgFG/lgFT)]
    try:
        factor = (2.0/3.0) - (0.5 * (lgAST/lgFG)) / (2.0 * (lgFG/max(lgFT,1e-9)))
    except Exception:
        factor = 2.0/3.0
    # VOP = lgPTS / (lgFGA - lgORB + lgTOV + 0.44*lgFTA)
    # Need lgTOV — not directly in team totals pre-1978, but we have it (TOV)
    lgTOV = float(lg["TOV"].iloc[0])
    VOP = lgPTS / max((lgFGA - lgORB + lgTOV + 0.44*lgFTA), 1e-9)
    # DRBP = (lgTRB - lgORB) / lgTRB
    DRBP = (lgTRB - lgORB) / max(lgTRB, 1e-9)
    return {
        "factor": factor, "VOP": VOP, "DRBP": DRBP,
        "lgFT": lgFT, "lgFTA": lgFTA, "lgFG": lgFG, "lgAST": lgAST,
        "lgTRB": lgTRB, "lgORB": lgORB, "lgPTS": lgPTS, "lgPF": lgPF
    }

def get_player_shotchart(player_id, season, season_type="Regular Season", refresh=False):
    """
    Fetch shot chart data for a player for a given season and season type.
    Uses nba_api ShotChartDetail and caches to CSV:

        data/cache/shotchart_player_{player_id}_{season}_{season_type}.csv

    Returns a DataFrame with at least:
    LOC_X, LOC_Y, SHOT_MADE_FLAG, SHOT_ZONE_BASIC, SHOT_DISTANCE, GAME_DATE, PERIOD, ACTION_TYPE, SHOT_TYPE
    """
    if not player_id or not season:
        return pd.DataFrame()

    tag = season_type.replace(" ", "_")
    cp = _p(f"shotchart_player_{player_id}_{season}_{tag}.csv")

    if cp.exists() and not refresh:
        try:
            return _load_csv(cp)
        except Exception:
            pass  # fall through and refetch

    try:
        res = shotchartdetail.ShotChartDetail(
            team_id=0,  # 0 => all teams for that player
            player_id=player_id,
            season_nullable=season,
            season_type_all_star=season_type,
            context_measure_simple="FGA",
            timeout=40,
        )
        df = res.get_data_frames()[0]

        if df.empty:
            return pd.DataFrame()

        keep = [
            "LOC_X",
            "LOC_Y",
            "SHOT_MADE_FLAG",
            "SHOT_ZONE_BASIC",
            "SHOT_DISTANCE",
            "GAME_DATE",
            "PERIOD",
            "ACTION_TYPE",
            "SHOT_TYPE",
        ]
        keep = [c for c in keep if c in df.columns]

        df = df[keep].copy()

        # basic cleaning: restrict to half-court area used in most examples
        if "LOC_Y" in df.columns:
            df = df[df["LOC_Y"] <= 470]

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

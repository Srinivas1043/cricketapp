from typing import List, Dict, Any

def generate_round_robin_fixtures(teams: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Generates a round-robin schedule for the list of teams.
    Uses the Circle Method.
    Supports 10 teams (9 rounds, 5 matches per round, total 45 matches).
    """
    n = len(teams)
    if n % 2 != 0:
        # If odd number of teams, add a dummy team for byes, but we assume exactly 10 teams here
        return []
        
    fixtures = []
    
    # We copy the list to avoid mutating the input
    list_teams = list(teams)
    
    # Standard Circle Method
    # Keep team 0 fixed, rotate others
    num_rounds = n - 1
    matches_per_round = n // 2
    
    venues = [
        "Wankhede Stadium, Mumbai", 
        "M. A. Chidambaram Stadium, Chennai", 
        "M. Chinnaswamy Stadium, Bengaluru", 
        "Eden Gardens, Kolkata", 
        "Sawai Mansingh Stadium, Jaipur",
        "Arun Jaitley Stadium, Delhi",
        "Rajiv Gandhi Intl Stadium, Hyderabad",
        "Ekana Cricket Stadium, Lucknow",
        "Narendra Modi Stadium, Ahmedabad",
        "PCA Stadium, Mohali"
    ]
    
    for r in range(num_rounds):
        round_name = f"ROUND_{r + 1}"
        for i in range(matches_per_round):
            home_idx = i
            away_idx = n - 1 - i
            
            home_team = list_teams[home_idx]
            away_team = list_teams[away_idx]
            
            # Alternating venues
            venue = home_team.get("home_ground", venues[home_idx % len(venues)])
            
            fixtures.append({
                "team1_id": home_team["id"],
                "team2_id": away_team["id"],
                "venue": venue,
                "stage": round_name,
                "status": "UPCOMING"
            })
            
        # Rotate the teams (except the first one)
        list_teams = [list_teams[0]] + [list_teams[-1]] + list_teams[1:-1]
        
    return fixtures

def convert_overs_to_balls(overs: float) -> int:
    """
    Converts over format (e.g. 15.4) to ball count.
    """
    overs_int = int(overs)
    balls = int(round((overs - overs_int) * 10))
    return (overs_int * 6) + balls

def convert_balls_to_overs(balls: int) -> float:
    """
    Converts ball count to over format (e.g. 94 balls -> 15.4 overs).
    """
    overs = balls // 6
    remaining_balls = balls % 6
    return overs + (remaining_balls / 10.0)

def recalculate_standings(teams: List[Dict[str, Any]], matches: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Recalculates points table for all teams based on completed matches.
    Calculates Wins, Losses, Points, and Net Run Rate (NRR).
    
    NRR Formula:
      NRR = (Total Runs Scored / Total Overs Faced) - (Total Runs Conceded / Total Overs Bowled)
      
    Note: If a team is bowled out, they are considered to have faced their full quota of 20 overs.
    """
    # Initialize stats for each team
    standings = {}
    for t in teams:
        standings[t["id"]] = {
            "id": t["id"],
            "name": t["name"],
            "short_name": t["short_name"],
            "wins": 0,
            "losses": 0,
            "points": 0,
            "nrr": 0.0,
            "runs_scored": 0,
            "balls_faced_effective": 0,
            "runs_conceded": 0,
            "balls_bowled_effective": 0,
            "is_ai": t["is_ai"]
        }
        
    for m in matches:
        if m["status"] != "COMPLETED":
            continue
            
        t1_id = m["team1_id"]
        t2_id = m["team2_id"]
        
        # Verify both teams exist in standings
        if t1_id not in standings or t2_id not in standings:
            continue
            
        sc = m.get("scorecard", {})
        if not sc:
            continue
            
        r1 = sc["innings1"]["total_runs"]
        w1 = sc["innings1"]["total_wickets"]
        o1 = sc["innings1"]["total_overs"]
        
        r2 = sc["innings2"]["total_runs"]
        w2 = sc["innings2"]["total_wickets"]
        o2 = sc["innings2"]["total_overs"]
        
        # Standard T20 overs cap
        quota_balls = 120 # 20 overs
        
        # Effective balls faced (if 10 wickets down, counts as full 20 overs)
        b1_faced = quota_balls if w1 >= 10 else convert_overs_to_balls(o1)
        b2_faced = quota_balls if w2 >= 10 else convert_overs_to_balls(o2)
        
        # Update runs/balls for NRR
        # Innings 1 batting = Team 1, bowling = Team 2
        # Innings 2 batting = Team 2, bowling = Team 1
        standings[t1_id]["runs_scored"] += r1
        standings[t1_id]["balls_faced_effective"] += b1_faced
        standings[t1_id]["runs_conceded"] += r2
        standings[t1_id]["balls_bowled_effective"] += b2_faced
        
        standings[t2_id]["runs_scored"] += r2
        standings[t2_id]["balls_faced_effective"] += b2_faced
        standings[t2_id]["runs_conceded"] += r1
        standings[t2_id]["balls_bowled_effective"] += b1_faced
        
        # Determine match winner
        # Team 1 wins if Innings 1 score > Innings 2 score
        # Since target in innings 2 is score1 + 1
        if r2 >= r1 + 1:
            standings[t2_id]["wins"] += 1
            standings[t2_id]["points"] += 2
            standings[t1_id]["losses"] += 1
        elif r1 > r2:
            standings[t1_id]["wins"] += 1
            standings[t1_id]["points"] += 2
            standings[t2_id]["losses"] += 1
        else:
            # Tie (split points)
            standings[t1_id]["points"] += 1
            standings[t2_id]["points"] += 1
            
    # Calculate NRR for each team
    for t_id, stats in standings.items():
        runs_sc = stats["runs_scored"]
        balls_fc = stats["balls_faced_effective"]
        runs_cc = stats["runs_conceded"]
        balls_bw = stats["balls_bowled_effective"]
        
        # Convert balls to decimal overs for NRR divisor (e.g. 120 balls -> 20.0 overs)
        overs_fc_dec = balls_fc / 6.0
        overs_bw_dec = balls_bw / 6.0
        
        nrr = 0.0
        if overs_fc_dec > 0 and overs_bw_dec > 0:
            nrr_scored = runs_sc / overs_fc_dec
            nrr_conceded = runs_cc / overs_bw_dec
            nrr = nrr_scored - nrr_conceded
            
        stats["nrr"] = round(nrr, 3)
        
    # Convert standings dict to list and sort by:
    # 1. Points (descending)
    # 2. Wins (descending)
    # 3. NRR (descending)
    # 4. Name (alphabetical)
    standings_list = list(standings.values())
    standings_list.sort(key=lambda x: (x["points"], x["wins"], x["nrr"]), reverse=True)
    
    return standings_list

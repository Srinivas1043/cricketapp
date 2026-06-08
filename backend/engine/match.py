import random
from typing import Dict, Any, List, Generator, Tuple

# Commentary templates for rich gameplay feedback
COMMENTARY_TEMPLATES = {
    "dot": [
        "Good length ball, defended back to the bowler.",
        "Swing and a miss! Beats the outside edge.",
        "Tucked away straight to the fielder at mid-wicket. No run.",
        "Slow delivery outside off, batsman decides to let it go.",
        "Quick bouncer! Batsman ducks under it.",
        "Solid block forward. The fielder cleans it up quickly."
    ],
    "1": [
        "Guided away to third man for a single.",
        "Flicked off the pads to deep square leg to rotate the strike.",
        "Pushed into the gap at cover for a quick single.",
        "Direct hit would have been close, but they scramble through for one.",
        "A gentle tap to mid-off and they run hard.",
        "Outside edge runs down to short third man, single taken."
    ],
    "2": [
        "Placed nicely into the gap at deep mid-wicket. Excellent running for two.",
        "Chipped over the infield. They hurry back for the second run.",
        "Slashed to deep point. Easy brace for the batsmen.",
        "Driven past cover, the fielder chases and slides to save the boundary. Two runs.",
        "Strayed onto the pads, tucked away to fine leg for a couple."
    ],
    "3": [
        "Struck well through the covers, the outfield is slow and they pick up three.",
        "Pulled away to deep square leg. Brilliant effort in the deep prevents the boundary. Three runs.",
        "Lofted towards long-on, the fielder sprints and saves it just in time. Excellent running."
    ],
    "4": [
        "CRACK! Driven elegantly through the covers for a boundary! Sublime shot.",
        "Strayed on the leg side and flicked away fine. The ball races to the boundary!",
        "Short ball pulled away imperiously! One bounce and over the ropes.",
        "Edged! But it flies past the slip fielder and runs away to the boundary.",
        "Overpitched and smashed straight back past the bowler! Four runs.",
        "Reverse sweep executed to perfection! Races away to the third-man boundary."
    ],
    "6": [
        "BOOM! Down the track and launched way over long-on for a massive SIX!",
        "Struck beautifully! Just a flick of the wrists and it sails over deep square leg!",
        "Slog sweep connected cleanly! High and handsome into the crowd!",
        "Short ball pulled with raw power, clears the deep mid-wicket boundary easily!",
        "Lofted over extra cover! It goes all the way! What a spectacular shot!"
    ],
    "wicket": [
        "OUT! Clean bowled! The bowler executes the yorker perfectly, stumps are shattered!",
        "OUT! In the air... and taken! The batsman tries to go big but finds the fielder at long-off.",
        "OUT! LBW! Plumb in front! The batsman walks off without even considering a review.",
        "OUT! Edged and taken! Safe hands by the wicketkeeper. Massive breakthrough!",
        "OUT! Direct hit! The batsman pushed for a risky single and is caught well short of the crease!",
        "OUT! Soft dismissal! Chipped straight to the fielder at short cover."
    ],
    "wide": [
        "Wide ball. Strayed down the leg side.",
        "Wide ball. Bowled way outside the off stump guideline.",
        "Wide bouncer, sails over the batsman's head."
    ],
    "no_ball": [
        "No ball! Bowler overstepped the line. Free hit coming up!",
        "No ball! High full toss above waist height. Free hit!"
    ]
}

def get_commentary(outcome: str, batsman_name: str, bowler_name: str) -> str:
    templates = COMMENTARY_TEMPLATES.get(outcome, ["Delivery completed."])
    base_text = random.choice(templates)
    return f"{bowler_name} to {batsman_name}: {base_text}"

class MatchSimulator:
    def __init__(self, match_data: Dict[str, Any]):
        """
        match_data contains structure:
        {
           "team1": {"id": "...", "name": "...", "short_name": "...", "starting_11": [...players...]},
           "team2": {"id": "...", "name": "...", "short_name": "...", "starting_11": [...players...]},
           "venue": "...",
           "pitch_type": "SPIN" | "PACE" | "NEUTRAL",
           "scorecard": {...existing scorecard or empty...}
        }
        """
        self.team1 = match_data["team1"]
        self.team2 = match_data["team2"]
        self.venue = match_data["venue"]
        self.pitch_type = match_data.get("pitch_type", "NEUTRAL")
        
        # Load or initialize scorecard
        self.scorecard = match_data.get("scorecard", {})
        if not self.scorecard:
            self.init_scorecard()

    def init_scorecard(self):
        self.scorecard = {
            "innings1": {
                "team_id": self.team1["id"],
                "team_name": self.team1["name"],
                "batting": [],
                "bowling": [],
                "fall_of_wickets": [],
                "total_runs": 0,
                "total_wickets": 0,
                "total_overs": 0.0,
                "balls_bowled": 0,
                "extras": 0,
                "history": []
            },
            "innings2": {
                "team_id": self.team2["id"],
                "team_name": self.team2["name"],
                "batting": [],
                "bowling": [],
                "fall_of_wickets": [],
                "total_runs": 0,
                "total_wickets": 0,
                "total_overs": 0.0,
                "balls_bowled": 0,
                "extras": 0,
                "history": []
            },
            "current_innings_num": 1,
            "target": None,
            "status": "UPCOMING",
            "result": None,
            "drs_available": {self.team1["id"]: 2, self.team2["id"]: 2},
            "current_batsmen": [],
            "current_bowler_id": None,
            "batting_order_idx": 0,
            "bowlers_used_this_innings": []
        }
        
        # Innings 1: Team 1 bats, Team 2 bowls
        self._init_batting_scorecard_slots("innings1", self.team1["starting_11"])
        self._init_bowling_scorecard_slots("innings1", self.team2["starting_11"])
        
        # Innings 2: Team 2 bats, Team 1 bowls
        self._init_batting_scorecard_slots("innings2", self.team2["starting_11"])
        self._init_bowling_scorecard_slots("innings2", self.team1["starting_11"])

    def _init_batting_scorecard_slots(self, innings_key: str, players: List[Dict[str, Any]]):
        sorted_players = sorted(players, key=lambda x: x.get("batting_order") or 99)
        for idx, p in enumerate(sorted_players):
            self.scorecard[innings_key]["batting"].append({
                "id": p["id"],
                "name": p["name"],
                "runs": 0,
                "balls": 0,
                "fours": 0,
                "sixes": 0,
                "status": "DNB",
                "how_out": ""
            })

    def _init_bowling_scorecard_slots(self, innings_key: str, players: List[Dict[str, Any]]):
        for p in players:
            if p["role"] in ["bowler", "allrounder"]:
                self.scorecard[innings_key]["bowling"].append({
                    "id": p["id"],
                    "name": p["name"],
                    "overs": 0.0,
                    "balls": 0,
                    "maidens": 0,
                    "runs": 0,
                    "wickets": 0,
                    "bowling_order": p.get("bowling_order") or 99
                })

    def start_innings(self):
        curr_inn_num = self.scorecard["current_innings_num"]
        inn_key = "innings1" if curr_inn_num == 1 else "innings2"
        batting_team = self.team1 if curr_inn_num == 1 else self.team2
        
        # Set first two batsmen
        self.scorecard[inn_key]["batting"][0]["status"] = "BAT-STRIKER"
        self.scorecard[inn_key]["batting"][1]["status"] = "BAT-NONSTRIKER"
        self.scorecard["current_batsmen"] = [
            self.scorecard[inn_key]["batting"][0]["id"],
            self.scorecard[inn_key]["batting"][1]["id"]
        ]
        self.scorecard["batting_order_idx"] = 2
        self.scorecard["status"] = "LIVE"
        
        # Pick default bowler (lowest bowling_order index)
        bowling_team_key = "innings1" if curr_inn_num == 2 else "innings2"
        # Since innings 1 batting is team1, innings 1 bowling is team2!
        # Let's verify: 
        # Innings 1: Team 1 Bats, Team 2 Bowls. So bowling scorecard is in innings1
        # Innings 2: Team 2 Bats, Team 1 Bowls. So bowling scorecard is in innings2
        bowling_pool = self.scorecard[inn_key]["bowling"]
        if bowling_pool:
            default_bowler = min(bowling_pool, key=lambda x: x["bowling_order"])
            self.scorecard["current_bowler_id"] = default_bowler["id"]
            if default_bowler["id"] not in self.scorecard["bowlers_used_this_innings"]:
                self.scorecard["bowlers_used_this_innings"].append(default_bowler["id"])

    def simulate_ball(self) -> Dict[str, Any]:
        """
        Simulates one ball, updates scorecard, and returns the ball event detail.
        """
        if self.scorecard["status"] != "LIVE":
            return {"error": "Match is not live."}
            
        curr_inn_num = self.scorecard["current_innings_num"]
        inn_key = "innings1" if curr_inn_num == 1 else "innings2"
        inn_data = self.scorecard[inn_key]
        
        # 1. Fetch current batsman & bowler
        striker_id = self.scorecard["current_batsmen"][0]
        non_striker_id = self.scorecard["current_batsmen"][1]
        bowler_id = self.scorecard["current_bowler_id"]
        
        batting_team = self.team1 if curr_inn_num == 1 else self.team2
        bowling_team = self.team2 if curr_inn_num == 1 else self.team1
        
        batsman_data = next(b for b in inn_data["batting"] if b["id"] == striker_id)
        bowler_data = next(b for b in inn_data["bowling"] if b["id"] == bowler_id)
        
        # Fetch detailed stats from starting_11 configs for calculations
        bat_profile = next(p for p in batting_team["starting_11"] if p["id"] == striker_id)
        bowl_profile = next(p for p in bowling_team["starting_11"] if p["id"] == bowler_id)
        
        # 2. Probability engine factors
        # Innings phase
        legal_balls = inn_data["balls_bowled"]
        over_num = legal_balls // 6 + 1
        
        phase = "MIDDLE"
        if over_num <= 6:
            phase = "POWERPLAY"
        elif over_num >= 16:
            phase = "DEATH"
            
        # Form and fitness weights
        bat_form = bat_profile.get("current_form", 0.5)
        bat_fit = bat_profile.get("fitness", 1.0)
        bowl_form = bowl_profile.get("current_form", 0.5)
        bowl_fit = bowl_profile.get("fitness", 1.0)
        
        # Pitch suitability
        pitch_multiplier_bat = 1.0
        pitch_multiplier_bowl = 1.0
        
        if self.pitch_type == bat_profile.get("pitch_suitability"):
            pitch_multiplier_bat = 1.15
        if self.pitch_type == bowl_profile.get("pitch_suitability"):
            pitch_multiplier_bowl = 1.15

        # Base player ratings
        # Batsman rating: combinations of strike rate and average, form, fitness
        bat_rating = (bat_profile["strike_rate"] * 0.4 + bat_profile["batting_avg"] * 0.6) * (bat_form * 0.8 + 0.6) * (bat_fit * 0.2 + 0.8) * pitch_multiplier_bat
        # Bowler rating: economy and avg, form, fitness
        # Economy (lower is better, so we use (12 - economy) or similar)
        bowl_rating = ((12.0 - bowl_profile["bowling_economy"]) * 8.0 + (50.0 - bowl_profile["bowling_avg"]) * 0.4) * (bowl_form * 0.8 + 0.6) * (bowl_fit * 0.2 + 0.8) * pitch_multiplier_bowl
        
        # Pressure factor
        pressure_factor = 1.0
        if curr_inn_num == 2 and self.scorecard["target"] is not None:
            runs_needed = self.scorecard["target"] - inn_data["total_runs"]
            balls_remaining = 120 - legal_balls
            if balls_remaining > 0:
                required_run_rate = (runs_needed / balls_remaining) * 6.0
                # If RRR > 10, pressure is high
                if required_run_rate > 10.0:
                    pressure_factor = min(2.0, required_run_rate / 8.0)
                elif required_run_rate < 4.0:
                    pressure_factor = 0.6

        # Calculate outcomes weights
        weights = {
            "dot": 40.0 * (bowl_rating / max(10.0, bat_rating * 0.8)),
            "1": 35.0,
            "2": 8.0,
            "3": 0.5,
            "4": 8.0 * (bat_rating / max(10.0, bowl_rating * 0.8)) * (1.3 if phase == "POWERPLAY" else 1.0),
            "6": 3.0 * (bat_rating / max(10.0, bowl_rating * 0.8)) * (1.5 if phase == "DEATH" else 1.0),
            "wicket": 3.5 * (bowl_rating / max(10.0, bat_rating * 0.8)) * (1.5 if phase == "DEATH" or pressure_factor > 1.4 else 1.0),
            "wide": 1.2,
            "no_ball": 0.3
        }
        
        # Adjust for phase modifiers
        if phase == "POWERPLAY":
            weights["dot"] *= 0.8
            weights["4"] *= 1.3
            weights["6"] *= 1.2
        elif phase == "DEATH":
            weights["dot"] *= 0.6
            weights["4"] *= 1.4
            weights["6"] *= 1.8
            weights["wicket"] *= 1.5
            
        # Draw outcome
        outcomes = list(weights.keys())
        prob_weights = list(weights.values())
        outcome = random.choices(outcomes, weights=prob_weights, k=1)[0]
        
        runs_scored = 0
        extra_runs = 0
        is_legal_ball = True
        wicket_fell = False
        
        # 3. Process outcome
        if outcome in ["1", "2", "3", "4", "6"]:
            runs_scored = int(outcome)
            batsman_data["runs"] += runs_scored
            batsman_data["balls"] += 1
            if outcome == "4":
                batsman_data["fours"] += 1
            elif outcome == "6":
                batsman_data["sixes"] += 1
                
            inn_data["total_runs"] += runs_scored
            bowler_data["runs"] += runs_scored
            
        elif outcome == "dot":
            batsman_data["balls"] += 1
            
        elif outcome == "wicket":
            batsman_data["balls"] += 1
            wicket_fell = True
            is_legal_ball = True
            inn_data["total_wickets"] += 1
            bowler_data["wickets"] += 1
            
            batsman_data["status"] = "OUT"
            batsman_data["how_out"] = f"c & b {bowler_data['name']}" if random.random() < 0.2 else f"b {bowler_data['name']}"
            if random.random() < 0.4:
                # Catch by fielder
                fielder_name = random.choice([p["name"] for p in bowling_team["starting_11"] if p["id"] != bowler_id])
                batsman_data["how_out"] = f"c {fielder_name} b {bowler_data['name']}"
                
        elif outcome == "wide":
            extra_runs = 1
            is_legal_ball = False
            inn_data["total_runs"] += 1
            inn_data["extras"] += 1
            bowler_data["runs"] += 1
            
        elif outcome == "no_ball":
            extra_runs = 1
            is_legal_ball = False
            inn_data["total_runs"] += 1
            inn_data["extras"] += 1
            bowler_data["runs"] += 1
            
        # 4. Update legal balls & overs
        if is_legal_ball:
            inn_data["balls_bowled"] += 1
            bowler_data["balls"] += 1
            # Recalculate bowler overs (e.g. 1.5 -> 2.0 or 0.5 -> 1.0)
            overs_completed = bowler_data["balls"] // 6
            overs_balls = bowler_data["balls"] % 6
            bowler_data["overs"] = overs_completed + (overs_balls / 10.0)
            
            # Recalculate team total overs
            team_overs_completed = inn_data["balls_bowled"] // 6
            team_overs_balls = inn_data["balls_bowled"] % 6
            inn_data["total_overs"] = team_overs_completed + (team_overs_balls / 10.0)
            
        # Swap strike if odd runs scored
        if runs_scored in [1, 3]:
            self.scorecard["current_batsmen"] = [non_striker_id, striker_id]
            
        # Generate commentary text
        comm = get_commentary(outcome, batsman_data["name"], bowler_data["name"])
        
        # Save ball details to history
        ball_idx = inn_data["balls_bowled"]
        over_ball_num = (ball_idx - 1) % 6 + 1 if is_legal_ball else (ball_idx % 6)
        over_ball_str = f"{(ball_idx - 1) // 6}.{over_ball_num}" if is_legal_ball else f"{ball_idx // 6}.{over_ball_num} (extra)"
        
        ball_event = {
            "over_ball": over_ball_str,
            "batsman": batsman_data["name"],
            "bowler": bowler_data["name"],
            "outcome": outcome,
            "runs": runs_scored + extra_runs,
            "commentary": comm,
            "team_score": f"{inn_data['total_runs']}/{inn_data['total_wickets']}"
        }
        inn_data["history"].append(ball_event)
        
        # Fall of wicket record
        if wicket_fell:
            inn_data["fall_of_wickets"].append(
                f"{inn_data['total_runs']}-{inn_data['total_wickets']} ({batsman_data['name']}, {over_ball_str})"
            )
            
        # 5. Check Innings/Match Complete Conditions
        match_complete = False
        innings_complete = False
        
        # Wicket fell: bring in new batsman if team still has wickets left
        if wicket_fell and inn_data["total_wickets"] < 10:
            next_idx = self.scorecard["batting_order_idx"]
            if next_idx < len(inn_data["batting"]):
                next_bat = inn_data["batting"][next_idx]
                next_bat["status"] = "BAT-STRIKER"
                # Put them on strike
                self.scorecard["current_batsmen"] = [next_bat["id"], non_striker_id]
                self.scorecard["batting_order_idx"] += 1
            else:
                innings_complete = True
        elif wicket_fell and inn_data["total_wickets"] >= 10:
            innings_complete = True
            
        # Target chased (innings 2)
        if curr_inn_num == 2 and self.scorecard["target"] is not None and inn_data["total_runs"] >= self.scorecard["target"]:
            innings_complete = True
            match_complete = True
            
        # Overs finished (120 legal balls)
        if inn_data["balls_bowled"] >= 120:
            innings_complete = True
            
        # Process end of innings
        if innings_complete and not match_complete:
            if curr_inn_num == 1:
                # Innings 1 over: set target for Innings 2
                self.scorecard["target"] = inn_data["total_runs"] + 1
                self.scorecard["current_innings_num"] = 2
                # Reset batsmen / bowlers state
                self.scorecard["current_batsmen"] = []
                self.scorecard["current_bowler_id"] = None
                self.scorecard["bowlers_used_this_innings"] = []
                # Auto start second innings setup
                self.start_innings()
                ball_event["innings_change"] = True
                ball_event["commentary"] += f" End of Innings! {inn_data['team_name']} score {inn_data['total_runs']}/{inn_data['total_wickets']}. Target for {self.scorecard['innings2']['team_name']}: {self.scorecard['target']} runs."
            else:
                # Innings 2 over: match is complete!
                match_complete = True
                
        if match_complete:
            self.scorecard["status"] = "COMPLETED"
            self.scorecard["current_batsmen"] = []
            self.scorecard["current_bowler_id"] = None
            
            # Determine winner
            score1 = self.scorecard["innings1"]["total_runs"]
            score2 = self.scorecard["innings2"]["total_runs"]
            
            # Team names
            name1 = self.scorecard["innings1"]["team_name"]
            name2 = self.scorecard["innings2"]["team_name"]
            
            if score2 >= self.scorecard["target"]:
                wickets_left = 10 - self.scorecard["innings2"]["total_wickets"]
                res = f"{name2} won by {wickets_left} wickets"
                self.scorecard["result"] = res
            elif score1 > score2:
                runs_diff = score1 - score2
                res = f"{name1} won by {runs_diff} runs"
                self.scorecard["result"] = res
            else:
                res = "Match Tied!"
                self.scorecard["result"] = res
                
            ball_event["match_complete"] = True
            ball_event["commentary"] += f" Match Over! {res}."
            
        # Over boundary: swap strike (except if end of innings)
        if is_legal_ball and inn_data["balls_bowled"] % 6 == 0 and not innings_complete:
            # Over completed: swap strike
            st_id, non_st_id = self.scorecard["current_batsmen"]
            self.scorecard["current_batsmen"] = [non_st_id, st_id]
            ball_event["over_completed"] = True
            
        return ball_event

    def change_bowler(self, new_bowler_id: str) -> bool:
        """
        Changes the bowler for the next over.
        """
        curr_inn_num = self.scorecard["current_innings_num"]
        inn_key = "innings1" if curr_inn_num == 1 else "innings2"
        
        # Verify bowler belongs to the bowling team
        bowling_team_key = "innings1" if curr_inn_num == 2 else "innings2"
        # Bowler is registered in the list
        bowlers = [b["id"] for b in self.scorecard[inn_key]["bowling"]]
        if new_bowler_id in bowlers:
            # Check maximum overs (4 per bowler in T20)
            bowler_stats = next(b for b in self.scorecard[inn_key]["bowling"] if b["id"] == new_bowler_id)
            if bowler_stats["balls"] >= 24:
                return False # Bowler bowled maximum overs
                
            self.scorecard["current_bowler_id"] = new_bowler_id
            if new_bowler_id not in self.scorecard["bowlers_used_this_innings"]:
                self.scorecard["bowlers_used_this_innings"].append(new_bowler_id)
            return True
        return False

    def exercise_drs(self, appealing_team_id: str) -> Dict[str, Any]:
        """
        Simulates DRS. 30% chance of overturning a wicket or checking review.
        """
        # Deduct DRS review count
        if appealing_team_id not in self.scorecard["drs_available"]:
            return {"error": "Invalid team"}
            
        if self.scorecard["drs_available"][appealing_team_id] <= 0:
            return {"error": "No DRS reviews left"}
            
        self.scorecard["drs_available"][appealing_team_id] -= 1
        
        curr_inn_num = self.scorecard["current_innings_num"]
        inn_key = "innings1" if curr_inn_num == 1 else "innings2"
        inn_data = self.scorecard[inn_key]
        
        # Check if last ball was a wicket or a dot to challenge
        if not inn_data["history"]:
            return {"error": "No balls bowled yet"}
            
        last_ball = inn_data["history"][-1]
        
        # Simulating review outcome
        overturned = random.random() < 0.35 # 35% chance review succeeds
        
        if last_ball["outcome"] == "wicket":
            # Challenging a wicket
            if overturned:
                # Wicket is saved! Revert wicket stats.
                # Find batsman who got out
                out_batsman = next((b for b in inn_data["batting"] if b["status"] == "OUT"), None)
                # If they just got out on the last ball, revert
                if out_batsman and last_ball["commentary"].find(out_batsman["name"]) != -1:
                    out_batsman["status"] = "BAT-STRIKER"
                    out_batsman["how_out"] = ""
                    inn_data["total_wickets"] -= 1
                    
                    # Revert bowler wicket
                    bowler_id = self.scorecard["current_bowler_id"]
                    bowler_data = next(b for b in inn_data["bowling"] if b["id"] == bowler_id)
                    bowler_data["wickets"] -= 1
                    
                    # Remove from fall of wickets
                    if inn_data["fall_of_wickets"]:
                        inn_data["fall_of_wickets"].pop()
                        
                    # Put them back in current batsmen
                    non_striker_id = self.scorecard["current_batsmen"][1] if len(self.scorecard["current_batsmen"]) > 1 else None
                    self.scorecard["current_batsmen"] = [out_batsman["id"], non_striker_id]
                    self.scorecard["batting_order_idx"] -= 1
                    
                    last_ball["outcome"] = "dot"
                    last_ball["runs"] = 0
                    last_ball["commentary"] = f"DRS REVIEW: Decision Overturned! Not Out. {last_ball['commentary']}"
                    last_ball["team_score"] = f"{inn_data['total_runs']}/{inn_data['total_wickets']}"
                    
                    # Restore review since it succeeded
                    self.scorecard["drs_available"][appealing_team_id] += 1
                    return {"status": "SUCCESS", "message": "Decision Overturned: NOT OUT!", "scorecard": self.scorecard}
            
            # Review failed
            last_ball["commentary"] = f"DRS REVIEW: Decision Stands! OUT. {last_ball['commentary']}"
            return {"status": "FAILED", "message": "Review Failed: OUT!", "scorecard": self.scorecard}
            
        else:
            # Challenging a dot ball to get a wicket
            if overturned:
                # It is OUT!
                striker_id = self.scorecard["current_batsmen"][0]
                batsman_data = next(b for b in inn_data["batting"] if b["id"] == striker_id)
                bowler_id = self.scorecard["current_bowler_id"]
                bowler_data = next(b for b in inn_data["bowling"] if b["id"] == bowler_id)
                
                batsman_data["status"] = "OUT"
                batsman_data["how_out"] = f"lbw b {bowler_data['name']} (DRS)"
                
                inn_data["total_wickets"] += 1
                bowler_data["wickets"] += 1
                
                over_ball_str = last_ball["over_ball"]
                inn_data["fall_of_wickets"].append(
                    f"{inn_data['total_runs']}-{inn_data['total_wickets']} ({batsman_data['name']}, {over_ball_str})"
                )
                
                last_ball["outcome"] = "wicket"
                last_ball["commentary"] = f"DRS REVIEW: Decision Overturned! OUT. {last_ball['commentary']}"
                last_ball["team_score"] = f"{inn_data['total_runs']}/{inn_data['total_wickets']}"
                
                # Bring in new batsman if wickets < 10
                if inn_data["total_wickets"] < 10:
                    next_idx = self.scorecard["batting_order_idx"]
                    if next_idx < len(inn_data["batting"]):
                        next_bat = inn_data["batting"][next_idx]
                        next_bat["status"] = "BAT-STRIKER"
                        non_striker_id = self.scorecard["current_batsmen"][1]
                        self.scorecard["current_batsmen"] = [next_bat["id"], non_striker_id]
                        self.scorecard["batting_order_idx"] += 1
                    else:
                        self.scorecard["status"] = "COMPLETED" # Innings complete
                else:
                    self.scorecard["status"] = "COMPLETED"
                    
                # Restore review since it succeeded
                self.scorecard["drs_available"][appealing_team_id] += 1
                return {"status": "SUCCESS", "message": "Decision Overturned: OUT!", "scorecard": self.scorecard}
                
            last_ball["commentary"] = f"DRS REVIEW: Decision Stands! NOT OUT. {last_ball['commentary']}"
            return {"status": "FAILED", "message": "Review Failed: NOT OUT!", "scorecard": self.scorecard}

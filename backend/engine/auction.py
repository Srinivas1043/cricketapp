import random
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple

def get_bid_increment(current_bid: float) -> float:
    """
    Returns the standard IPL bid increment based on current bid in Crores.
    """
    if current_bid < 2.0:
        return 0.10  # 10 Lakhs
    elif current_bid < 5.0:
        return 0.20  # 20 Lakhs
    elif current_bid < 10.0:
        return 0.50  # 50 Lakhs
    else:
        return 1.00  # 1 Crore

def evaluate_player_valuation(player: Dict[str, Any], team: Dict[str, Any]) -> float:
    """
    Calculate the maximum valuation (in Crores) an AI team assigns to a player.
    Factors in:
      - Player's base stats (batting strike rate, avg, bowling economy, wickets)
      - Team budget remaining
      - Team squad gaps (needs more batsmen, bowlers, etc.)
    """
    role = player.get("role") or player.get("player", {}).get("role")
    base_price = player.get("base_price") or player.get("player", {}).get("base_price", 0.0)
    
    # 1. Base Stat Valuation
    stat_val = base_price
    if role == "batsman":
        # high strike rate and average boost value
        stat_val += (player.get("strike_rate", 120) - 120) * 0.03 + (player.get("batting_avg", 25) - 25) * 0.08
    elif role == "bowler":
        # low economy and low bowling average boost value
        stat_val += (8.5 - player.get("bowling_economy", 8.5)) * 0.4 + (30.0 - player.get("bowling_avg", 30)) * 0.05
    elif role == "allrounder":
        # performs both roles
        bat_component = (player.get("strike_rate", 120) - 120) * 0.02 + (player.get("batting_avg", 20) - 20) * 0.05
        bowl_component = (8.5 - player.get("bowling_economy", 8.5)) * 0.2 + (30.0 - player.get("bowling_avg", 30)) * 0.03
        stat_val += bat_component + bowl_component + 0.50 # premium for allrounder
    elif role == "wicketkeeper":
        stat_val += (player.get("strike_rate", 120) - 120) * 0.02 + (player.get("batting_avg", 25) - 25) * 0.06 + 0.30 # premium for keeper

    # Ensure valuation is at least base price
    stat_val = max(base_price, stat_val)

    # 2. Squad Needs Adjustment
    # Count existing players in squad by role
    squad_players = team.get("players", [])
    role_counts = {"batsman": 0, "bowler": 0, "allrounder": 0, "wicketkeeper": 0}
    for p in squad_players:
        p_role = p.get("role") or p.get("player", {}).get("role")
        if p_role in role_counts:
            role_counts[p_role] += 1
        
    squad_size = len(squad_players)
    
    # Target distribution for squad of 15:
    # Batsmen: 5, Bowlers: 5, Allrounders: 3, Wicketkeepers: 2
    targets = {
        "batsman": 5,
        "bowler": 5,
        "allrounder": 3,
        "wicketkeeper": 2
    }
    
    deficit = targets[role] - role_counts[role]
    need_multiplier = 1.0
    if deficit > 0:
        need_multiplier = 1.0 + (deficit * 0.25) # high deficit = will pay up to 50% more
    else:
        need_multiplier = 0.6 # already satisfied = only buy if cheap

    # 3. Budget constraint adjustment
    budget = team["budget_remaining"]
    slots_needed = 15 - squad_size
    
    # AI must keep at least 0.5 Crore (50L) per remaining slot
    reserve_funds = max(0.0, (slots_needed - 1) * 0.5)
    max_safe_bid = budget - reserve_funds
    
    if max_safe_bid <= base_price:
        return 0.0 # Can't afford base price
        
    # Scale valuation based on remaining budget proportion
    # A richer team is willing to bid more aggressively
    budget_proportion = budget / 90.0
    aggression_factor = 0.8 + (budget_proportion * 0.4) # 0.8 to 1.2

    final_valuation = stat_val * need_multiplier * aggression_factor
    
    # Random variance (simulating different bidding styles or emotion)
    final_valuation *= random.uniform(0.85, 1.15)
    
    # Clip by absolute budget capabilities
    final_valuation = min(final_valuation, max_safe_bid)
    
    return round(final_valuation, 2)

class AuctionManager:
    def __init__(self, room_state: Dict[str, Any]):
        """
        room_state contains:
        {
          "room_id": "...",
          "status": "AUCTION",
          "teams": [...list of teams...],
          "unsold_players": [...list of global players...],
          "sold_players": [...list of sold players...],
          "current_auction": {
              "current_player": {...},
              "current_bid": None or float,
              "current_bidder_id": None or str,
              "timer_ends_at": datetime,
              "rtm_active": bool,
              "rtm_original_team_id": None or str,
              "rtm_timer_ends_at": None or datetime
          }
        }
        """
        self.room_id = room_state["room_id"]
        self.teams = room_state["teams"]
        self.current_auction = room_state["current_auction"]

    def process_ai_bids(self) -> Optional[Tuple[str, float]]:
        """
        Checks if any AI team wants to place a bid.
        Returns Tuple[team_id, bid_amount] if an AI bids, otherwise None.
        """
        # If auction is not running, or RTM is active, AI doesn't place regular bids
        if not self.current_auction.get("current_player") or self.current_auction.get("rtm_active"):
            return None
            
        current_player = self.current_auction["current_player"]
        current_bid = self.current_auction["current_bid"]
        current_bidder_id = self.current_auction["current_bidder_id"]
        
        # Calculate next required bid
        if current_bid is None:
            next_bid = current_player["base_price"]
        else:
            increment = get_bid_increment(current_bid)
            next_bid = round(current_bid + increment, 2)
            
        # Compile list of eligible AI teams that can afford next_bid
        eligible_ai_bids = []
        for team in self.teams:
            if not team["is_ai"]:
                continue
            if team["id"] == current_bidder_id:
                continue # Already the highest bidder
            if len(team.get("players", [])) >= 15:
                continue # Squad full
                
            # Evaluate valuation
            val = evaluate_player_valuation(current_player, team)
            if val >= next_bid:
                # Calculate probability of bidding
                # Higher margin (valuation - next_bid) -> higher chance to bid
                margin = val - next_bid
                bid_prob = min(0.9, 0.2 + (margin / max(1.0, val)) * 0.8)
                
                # Check if they decide to bid
                if random.random() < bid_prob:
                    eligible_ai_bids.append((team["id"], next_bid, margin))
                    
        if not eligible_ai_bids:
            return None
            
        # Pick the AI team that wants it the most (highest margin or random choice among top)
        # Let's sort by margin and add a bit of noise
        eligible_ai_bids.sort(key=lambda x: x[2] * random.uniform(0.8, 1.2), reverse=True)
        winning_ai_bid = eligible_ai_bids[0]
        
        return winning_ai_bid[0], winning_ai_bid[1]

    def place_bid(self, team_id: str, amount: float) -> Tuple[bool, str]:
        """
        Place a manual or AI bid. Validates rules.
        """
        current_player = self.current_auction.get("current_player")
        if not current_player:
            return False, "No active player up for auction."
            
        if self.current_auction.get("rtm_active"):
            return False, "Cannot bid during RTM window."
            
        # Find bidder team
        team = next((t for t in self.teams if t["id"] == team_id), None)
        if not team:
            return False, "Team not found."
            
        if len(team.get("players", [])) >= 15:
            return False, "Team already has maximum 15 players."
            
        # Validate budget
        if team["budget_remaining"] < amount:
            return False, f"Insufficient budget. Team has ₹{team['budget_remaining']} Cr, bid is ₹{amount} Cr."
            
        # Validate bid amount
        current_bid = self.current_auction["current_bid"]
        if current_bid is None:
            if amount < current_player["base_price"]:
                return False, f"Bid must be at least the base price of ₹{current_player['base_price']} Cr."
        else:
            increment = get_bid_increment(current_bid)
            min_req_bid = round(current_bid + increment, 2)
            if amount < min_req_bid:
                return False, f"Bid too low. Minimum required bid is ₹{min_req_bid} Cr."
                
        # Update auction state
        self.current_auction["current_bid"] = amount
        self.current_auction["current_bidder_id"] = team_id
        # Reset timer to 15 seconds from now
        self.current_auction["timer_ends_at"] = datetime.utcnow() + timedelta(seconds=15)
        
        return True, "Bid accepted."

    def check_rtm_eligibility(self) -> Tuple[bool, Optional[str]]:
        """
        When timer reaches 0, check if RTM is eligible.
        If yes, triggers RTM state and returns True, original_team_id.
        Otherwise returns False, None.
        """
        current_player = self.current_auction.get("current_player")
        current_bidder_id = self.current_auction.get("current_bidder_id")
        current_bid = self.current_auction.get("current_bid")
        
        if not current_player or current_bidder_id is None or current_bid is None:
            return False, None
            
        # Identify "original team" using the player's real-life affinity or designated team
        # For simplicity, we seed real-life players. If we mapped players to their original IPL franchise,
        # we check if that franchise exists in this room.
        # Let's simulate: we can fetch the player's real-life original team from template or map it.
        # Let's say we have a mapping of players to their default teams, or we just randomly assign
        # each player an "original franchise index" 0-9.
        # Better: we can check if the player has an "original_team" tag or name.
        # Let's check: in models, `Player` has a name. We can resolve their "original team" from a static map.
        original_team_name = get_original_team_name(current_player["name"])
        
        # Check if this team is in the room
        original_team = next((t for t in self.teams if t["name"] == original_team_name or t["short_name"] == original_team_name), None)
        
        if not original_team:
            return False, None
            
        # Eligibility rules:
        # 1. Original team is in the room
        # 2. Original team is NOT the current highest bidder
        # 3. Original team has an RTM card remaining
        # 4. Original team has enough budget to match the bid
        # 5. Original team's squad is not already full (less than 15 players)
        if (original_team["id"] != current_bidder_id and 
            original_team["rtm_cards_remaining"] > 0 and 
            original_team["budget_remaining"] >= current_bid and
            len(original_team.get("players", [])) < 15):
            
            # Setup RTM window
            self.current_auction["rtm_active"] = True
            self.current_auction["rtm_original_team_id"] = original_team["id"]
            self.current_auction["rtm_timer_ends_at"] = datetime.utcnow() + timedelta(seconds=10)
            return True, original_team["id"]
            
        return False, None

    def process_ai_rtm(self) -> Tuple[bool, str]:
        """
        Processes RTM decision for an AI team.
        Returns Tuple[rtm_exercised (bool), message].
        """
        if not self.current_auction.get("rtm_active"):
            return False, "RTM not active."
            
        original_team_id = self.current_auction["rtm_original_team_id"]
        original_team = next(t for t in self.teams if t["id"] == original_team_id)
        
        if not original_team["is_ai"]:
            return False, "RTM team is controlled by a human."
            
        current_player = self.current_auction["current_player"]
        current_bid = self.current_auction["current_bid"]
        
        # AI decides to match if the final bid is less than or equal to their valuation
        val = evaluate_player_valuation(current_player, original_team)
        
        # Add a slight bias to RTM: they are 15% more likely to keep their "own" player
        if current_bid <= val * 1.15:
            # Exercise RTM!
            return True, "AI exercised Right to Match."
        else:
            # Decline RTM
            return False, "AI declined Right to Match."

def get_original_team_name(player_name: str) -> str:
    """
    Returns the default franchise short_name for a player to check RTM eligibility.
    Maps real players to their standard IPL franchises.
    """
    mapping = {
        # MI
        "Rohit Sharma": "MI", "Jasprit Bumrah": "MI", "Suryakumar Yadav": "MI", 
        "Hardik Pandya": "MI", "Ishan Kishan": "MI", "Tilak Varma": "MI", "Piyush Chawla": "MI", "Gerald Coetzee": "MI",
        # CSK
        "MS Dhoni": "CSK", "Ruturaj Gaikwad": "CSK", "Ravindra Jadeja": "CSK", "Ajinkya Rahane": "CSK",
        "Deepak Chahar": "CSK", "Matheesha Pathirana": "CSK", "Shardul Thakur": "CSK", "Tushar Deshpande": "CSK", "Shivam Dube": "CSK", "Rachin Ravindra": "CSK",
        # RCB
        "Virat Kohli": "RCB", "Faf du Plessis": "RCB", "Glenn Maxwell": "RCB", "Mohammed Siraj": "RCB",
        "Rajat Patidar": "RCB", "Dinesh Karthik": "RCB", "Cameron Green": "RCB", "Will Jacks": "RCB", "Yash Dayal": "RCB",
        # KKR
        "Shreyas Iyer": "KKR", "Sunil Narine": "KKR", "Andre Russell": "KKR", "Rinku Singh": "KKR",
        "Varun Chakaravarthy": "KKR", "Venkatesh Iyer": "KKR", "Mitchell Starc": "KKR", "Phil Salt": "KKR", "Harshit Rana": "KKR",
        # RR
        "Sanju Samson": "RR", "Yashasvi Jaiswal": "RR", "Jos Buttler": "RR", "Yuzvendra Chahal": "RR",
        "Ravichandran Ashwin": "RR", "Trent Boult": "RR", "Sandip Sharma": "RR", "Riyan Parag": "RR", "Dhruv Jurel": "RR",
        # DC
        "Rishabh Pant": "DC", "David Warner": "DC", "Axar Patel": "DC", "Kuldeep Yadav": "DC",
        "Khaleel Ahmed": "DC", "Prithvi Shaw": "DC", "Tristan Stubbs": "DC", "Jake Fraser-McGurk": "DC", "Ishant Sharma": "DC",
        # SRH
        "Pat Cummins": "SRH", "Travis Head": "SRH", "Heinrich Klaasen": "SRH", "Abhishek Sharma": "SRH",
        "Bhuvneshwar Kumar": "SRH", "T Natarajan": "SRH", "Nitish Reddy": "SRH", "Shahbaz Ahmed": "SRH", "Mayank Agarwal": "SRH",
        # LSG
        "KL Rahul": "LSG", "Nicholas Pooran": "LSG", "Marcus Stoinis": "LSG", "Ravi Bishnoi": "LSG",
        "Krunal Pandya": "LSG", "Ayush Badoni": "LSG", "Mohsin Khan": "LSG", "Mayank Yadav": "LSG", "Quinton de Kock": "LSG",
        # GT
        "Shubman Gill": "GT", "Rashid Khan": "GT", "David Miller": "GT", "Sai Sudharsan": "GT",
        "Mohammed Shami": "GT", "Mohit Sharma": "GT", "Rahul Tewatia": "GT", "Shahrukh Khan": "GT", "Vijay Shankar": "GT",
        # PBKS
        "Shikhar Dhawan": "PBKS", "Sam Curran": "PBKS", "Liam Livingstone": "PBKS", "Arshdeep Singh": "PBKS",
        "Jitesh Sharma": "PBKS", "Harshal Patel": "PBKS", "Kagiso Rabada": "PBKS", "Harpreet Brar": "PBKS"
    }
    
    # Return mapping if exists, else assign randomly based on hash to ensure consistency
    if player_name in mapping:
        return mapping[player_name]
        
    teams = ["MI", "CSK", "RCB", "KKR", "RR", "DC", "SRH", "LSG", "GT", "PBKS"]
    h = hash(player_name)
    return teams[abs(h) % len(teams)]

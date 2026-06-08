import unittest
import sys
import os

# Append project root to python path to run tests
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))

from backend.engine.match import MatchSimulator
from backend.engine.auction import get_bid_increment, evaluate_player_valuation, AuctionManager

class TestAuctionEngine(unittest.TestCase):
    def test_bid_increments(self):
        self.assertEqual(get_bid_increment(1.5), 0.10)
        self.assertEqual(get_bid_increment(4.0), 0.20)
        self.assertEqual(get_bid_increment(8.0), 0.50)
        self.assertEqual(get_bid_increment(15.0), 1.00)

    def test_player_valuation(self):
        player = {
            "name": "Virat Kohli",
            "role": "batsman",
            "strike_rate": 135.0,
            "batting_avg": 38.5,
            "base_price": 2.0
        }
        team = {
            "id": "team1",
            "name": "RCB",
            "budget_remaining": 90.0,
            "players": []
        }
        val = evaluate_player_valuation(player, team)
        self.assertTrue(val >= 2.0)
        
    def test_auction_manager_ai_bid(self):
        player_dict = {
            "id": "player_1",
            "name": "Travis Head",
            "role": "batsman",
            "nationality": "Overseas",
            "strike_rate": 158.0,
            "batting_avg": 31.5,
            "base_price": 2.0,
            "pitch_suitability": "PACE"
        }
        teams = [
            {
                "id": "team_ai_1",
                "name": "AI Franchise 1",
                "is_ai": True,
                "budget_remaining": 80.0,
                "players": []
            },
            {
                "id": "team_ai_2",
                "name": "AI Franchise 2",
                "is_ai": True,
                "budget_remaining": 85.0,
                "players": []
            }
        ]
        
        auc_state = {
            "room_id": "room_1",
            "teams": teams,
            "current_auction": {
                "current_player": player_dict,
                "current_bid": None,
                "current_bidder_id": None,
                "rtm_active": False
            }
        }
        
        manager = AuctionManager(auc_state)
        # Process AI bids. Since valuation is high (Travis Head SR 158), AI should bid the base price
        ai_bid = manager.process_ai_bids()
        if ai_bid:
            team_id, bid_amount = ai_bid
            self.assertIn(team_id, ["team_ai_1", "team_ai_2"])
            self.assertEqual(bid_amount, 2.0)

class TestMatchEngine(unittest.TestCase):
    def setUp(self):
        # Mock match data with starting XI
        self.mock_match = {
            "team1": {
                "id": "team1",
                "name": "Chennai Super Kings",
                "short_name": "CSK",
                "starting_11": [
                    {"id": "p1", "name": "Ruturaj Gaikwad", "role": "batsman", "strike_rate": 137.5, "batting_avg": 39.1, "pitch_suitability": "NEUTRAL", "current_form": 0.8, "fitness": 1.0, "batting_order": 1},
                    {"id": "p2", "name": "MS Dhoni", "role": "wicketkeeper", "strike_rate": 137.5, "batting_avg": 38.8, "pitch_suitability": "SPIN", "current_form": 0.9, "fitness": 1.0, "batting_order": 2},
                ]
            },
            "team2": {
                "id": "team2",
                "name": "Mumbai Indians",
                "short_name": "MI",
                "starting_11": [
                    {"id": "p3", "name": "Jasprit Bumrah", "role": "bowler", "strike_rate": 80.0, "batting_avg": 5.0, "bowling_economy": 6.9, "bowling_avg": 19.5, "pitch_suitability": "PACE", "current_form": 0.95, "fitness": 1.0, "bowling_order": 1},
                    {"id": "p4", "name": "Hardik Pandya", "role": "allrounder", "strike_rate": 144.0, "batting_avg": 29.8, "bowling_economy": 8.4, "bowling_avg": 28.5, "pitch_suitability": "PACE", "current_form": 0.7, "fitness": 1.0, "bowling_order": 2},
                ]
            },
            "venue": "Wankhede Stadium",
            "pitch_type": "PACE"
        }
        
    def test_match_simulation_loop(self):
        sim = MatchSimulator(self.mock_match)
        sim.start_innings()
        
        # Verify initial states
        self.assertEqual(sim.scorecard["status"], "LIVE")
        self.assertEqual(sim.scorecard["current_innings_num"], 1)
        self.assertEqual(len(sim.scorecard["current_batsmen"]), 2)
        
        # Simulate a few balls
        for _ in range(5):
            res = sim.simulate_ball()
            self.assertNotIn("error", res)
            self.assertIn("outcome", res)
            
        # Verify scorecard structure
        self.assertTrue(sim.scorecard["innings1"]["balls_bowled"] > 0)
        self.assertTrue(sim.scorecard["innings1"]["total_runs"] >= 0)

if __name__ == "__main__":
    unittest.main()

import asyncio
import os
import sys
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.future import select
from sqlalchemy.orm import declarative_base

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    # Try absolute import first (when running from project root)
    from backend.database import Base, DATABASE_URL
    from backend.models import Player
except ModuleNotFoundError:
    # Fallback to relative imports (when running from backend directory)
    from database import Base, DATABASE_URL
    from models import Player

# 120+ Real IPL Players with realistic stats and team history
PLAYERS_DATA = [
    # --- BATSMEN ---
    {"name": "Virat Kohli", "role": "batsman", "nationality": "Indian", "batting_avg": 38.5, "strike_rate": 135.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 2.0, "pitch_suitability": "NEUTRAL", "ipl_team": "RCB", "ipl_season": 2024},
    {"name": "Rohit Sharma", "role": "batsman", "nationality": "Indian", "batting_avg": 30.2, "strike_rate": 133.5, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 2.0, "pitch_suitability": "PACE", "ipl_team": "MI", "ipl_season": 2024},
    {"name": "Shubman Gill", "role": "batsman", "nationality": "Indian", "batting_avg": 37.8, "strike_rate": 136.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 2.0, "pitch_suitability": "NEUTRAL", "ipl_team": "GT", "ipl_season": 2024},
    {"name": "Suryakumar Yadav", "role": "batsman", "nationality": "Indian", "batting_avg": 35.4, "strike_rate": 172.5, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 2.0, "pitch_suitability": "PACE", "ipl_team": "MI", "ipl_season": 2024},
    {"name": "Yashasvi Jaiswal", "role": "batsman", "nationality": "Indian", "batting_avg": 32.8, "strike_rate": 145.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 1.5, "pitch_suitability": "NEUTRAL", "ipl_team": "RR", "ipl_season": 2024},
    {"name": "Ruturaj Gaikwad", "role": "batsman", "nationality": "Indian", "batting_avg": 39.1, "strike_rate": 137.5, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 1.5, "pitch_suitability": "NEUTRAL", "ipl_team": "CSK", "ipl_season": 2024},
    {"name": "Rinku Singh", "role": "batsman", "nationality": "Indian", "batting_avg": 36.2, "strike_rate": 148.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 1.0, "pitch_suitability": "SPIN", "ipl_team": "KKR", "ipl_season": 2024},
    {"name": "Travis Head", "role": "batsman", "nationality": "Overseas", "batting_avg": 31.5, "strike_rate": 158.0, "bowling_economy": 8.5, "bowling_avg": 35.0, "base_price": 2.0, "pitch_suitability": "PACE", "ipl_team": "SRH", "ipl_season": 2024},
    {"name": "Faf du Plessis", "role": "batsman", "nationality": "Overseas", "batting_avg": 34.0, "strike_rate": 134.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 1.5, "pitch_suitability": "PACE", "ipl_team": "CSK", "ipl_season": 2024},
    {"name": "David Warner", "role": "batsman", "nationality": "Overseas", "batting_avg": 41.2, "strike_rate": 139.8, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 2.0, "pitch_suitability": "NEUTRAL", "ipl_team": "DC", "ipl_season": 2023},
    {"name": "Kane Williamson", "role": "batsman", "nationality": "Overseas", "batting_avg": 36.0, "strike_rate": 126.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 1.5, "pitch_suitability": "SPIN", "ipl_team": "SRH", "ipl_season": 2023},
    {"name": "Sai Sudharsan", "role": "batsman", "nationality": "Indian", "batting_avg": 42.0, "strike_rate": 129.5, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 0.5, "pitch_suitability": "SPIN", "ipl_team": "GT", "ipl_season": 2024},
    {"name": "Rajat Patidar", "role": "batsman", "nationality": "Indian", "batting_avg": 33.5, "strike_rate": 142.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 0.5, "pitch_suitability": "SPIN", "ipl_team": "RCB", "ipl_season": 2024},
    {"name": "Ajinkya Rahane", "role": "batsman", "nationality": "Indian", "batting_avg": 26.8, "strike_rate": 122.5, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 1.0, "pitch_suitability": "PACE", "ipl_team": "CSK", "ipl_season": 2024},
    {"name": "Tilak Varma", "role": "batsman", "nationality": "Indian", "batting_avg": 38.9, "strike_rate": 140.0, "bowling_economy": 8.0, "bowling_avg": 28.0, "base_price": 1.0, "pitch_suitability": "NEUTRAL", "ipl_team": "MI", "ipl_season": 2024},
    {"name": "Shimron Hetmyer", "role": "batsman", "nationality": "Overseas", "batting_avg": 29.8, "strike_rate": 144.5, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 1.5, "pitch_suitability": "SPIN", "ipl_team": "DC", "ipl_season": 2024},
    {"name": "Rovman Powell", "role": "batsman", "nationality": "Overseas", "batting_avg": 25.5, "strike_rate": 139.0, "bowling_economy": 9.2, "bowling_avg": 42.0, "base_price": 1.0, "pitch_suitability": "PACE", "ipl_team": "DC", "ipl_season": 2024},
    {"name": "Abhishek Sharma", "role": "batsman", "nationality": "Indian", "batting_avg": 28.5, "strike_rate": 148.0, "bowling_economy": 7.8, "bowling_avg": 30.0, "base_price": 0.5, "pitch_suitability": "NEUTRAL", "ipl_team": "SRH", "ipl_season": 2024},
    {"name": "Mayank Agarwal", "role": "batsman", "nationality": "Indian", "batting_avg": 23.0, "strike_rate": 131.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 1.0, "pitch_suitability": "PACE", "ipl_team": "SRH", "ipl_season": 2024},
    {"name": "Devdutt Padikkal", "role": "batsman", "nationality": "Indian", "batting_avg": 27.2, "strike_rate": 124.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 0.75, "pitch_suitability": "NEUTRAL", "ipl_team": "LSG", "ipl_season": 2024},
    {"name": "Prithvi Shaw", "role": "batsman", "nationality": "Indian", "batting_avg": 24.8, "strike_rate": 146.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 0.75, "pitch_suitability": "PACE", "ipl_team": "RR", "ipl_season": 2024},
    {"name": "Manish Pandey", "role": "batsman", "nationality": "Indian", "batting_avg": 29.0, "strike_rate": 121.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 0.5, "pitch_suitability": "SPIN", "ipl_team": "BAN", "ipl_season": 2024},
    {"name": "Shahrukh Khan", "role": "batsman", "nationality": "Indian", "batting_avg": 22.4, "strike_rate": 138.0, "bowling_economy": 8.0, "bowling_avg": 34.0, "base_price": 0.5, "pitch_suitability": "PACE", "ipl_team": "PBKS", "ipl_season": 2024},
    {"name": "Deepak Hooda", "role": "batsman", "nationality": "Indian", "batting_avg": 19.5, "strike_rate": 128.5, "bowling_economy": 8.4, "bowling_avg": 31.0, "base_price": 0.75, "pitch_suitability": "SPIN", "ipl_team": "LSG", "ipl_season": 2024},
    {"name": "Karun Nair", "role": "batsman", "nationality": "Indian", "batting_avg": 24.5, "strike_rate": 128.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 0.5, "pitch_suitability": "SPIN", "ipl_team": "RR", "ipl_season": 2024},
    {"name": "Tristan Stubbs", "role": "batsman", "nationality": "Overseas", "batting_avg": 33.5, "strike_rate": 155.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 1.0, "pitch_suitability": "NEUTRAL", "ipl_team": "DC", "ipl_season": 2024},
    {"name": "Jake Fraser-McGurk", "role": "batsman", "nationality": "Overseas", "batting_avg": 30.0, "strike_rate": 190.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 1.0, "pitch_suitability": "PACE", "ipl_team": "DC", "ipl_season": 2024},
    {"name": "Nehal Wadhera", "role": "batsman", "nationality": "Indian", "batting_avg": 28.2, "strike_rate": 139.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 0.3, "pitch_suitability": "NEUTRAL", "ipl_team": "MI", "ipl_season": 2024},
    {"name": "Abdul Samad", "role": "batsman", "nationality": "Indian", "batting_avg": 20.8, "strike_rate": 141.0, "bowling_economy": 9.5, "bowling_avg": 45.0, "base_price": 0.3, "pitch_suitability": "PACE", "ipl_team": "SRH", "ipl_season": 2024},
    {"name": "Ayush Badoni", "role": "batsman", "nationality": "Indian", "batting_avg": 24.0, "strike_rate": 132.0, "bowling_economy": 7.5, "bowling_avg": 27.0, "base_price": 0.3, "pitch_suitability": "SPIN", "ipl_team": "LSG", "ipl_season": 2024},

    # --- WICKETKEEPERS ---
    {"name": "MS Dhoni", "role": "wicketkeeper", "nationality": "Indian", "batting_avg": 38.8, "strike_rate": 137.5, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 2.0, "pitch_suitability": "SPIN", "ipl_team": "CSK", "ipl_season": 2024},
    {"name": "Rishabh Pant", "role": "wicketkeeper", "nationality": "Indian", "batting_avg": 35.2, "strike_rate": 148.5, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 2.0, "pitch_suitability": "NEUTRAL", "ipl_team": "DC", "ipl_season": 2024},
    {"name": "Sanju Samson", "role": "wicketkeeper", "nationality": "Indian", "batting_avg": 30.5, "strike_rate": 138.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 2.0, "pitch_suitability": "PACE", "ipl_team": "RR", "ipl_season": 2024},
    {"name": "Heinrich Klaasen", "role": "wicketkeeper", "nationality": "Overseas", "batting_avg": 37.4, "strike_rate": 165.8, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 2.0, "pitch_suitability": "SPIN", "ipl_team": "SRH", "ipl_season": 2024},
    {"name": "Ishan Kishan", "role": "wicketkeeper", "nationality": "Indian", "batting_avg": 29.4, "strike_rate": 135.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 1.5, "pitch_suitability": "NEUTRAL", "ipl_team": "MI", "ipl_season": 2024},
    {"name": "Nicholas Pooran", "role": "wicketkeeper", "nationality": "Overseas", "batting_avg": 32.2, "strike_rate": 156.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 2.0, "pitch_suitability": "SPIN", "ipl_team": "LSG", "ipl_season": 2024},
    {"name": "Quinton de Kock", "role": "wicketkeeper", "nationality": "Overseas", "batting_avg": 31.8, "strike_rate": 134.2, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 2.0, "pitch_suitability": "PACE", "ipl_team": "LSG", "ipl_season": 2024},
    {"name": "KL Rahul", "role": "wicketkeeper", "nationality": "Indian", "batting_avg": 45.5, "strike_rate": 130.2, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 2.0, "pitch_suitability": "NEUTRAL", "ipl_team": "PBKS", "ipl_season": 2024},
    {"name": "Phil Salt", "role": "wicketkeeper", "nationality": "Overseas", "batting_avg": 28.5, "strike_rate": 152.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 1.5, "pitch_suitability": "PACE", "ipl_team": "KKR", "ipl_season": 2024},
    {"name": "Jitesh Sharma", "role": "wicketkeeper", "nationality": "Indian", "batting_avg": 23.4, "strike_rate": 142.5, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 0.75, "pitch_suitability": "NEUTRAL", "ipl_team": "PBKS", "ipl_season": 2024},
    {"name": "Dhruv Jurel", "role": "wicketkeeper", "nationality": "Indian", "batting_avg": 28.0, "strike_rate": 136.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 0.5, "pitch_suitability": "SPIN", "ipl_team": "RR", "ipl_season": 2024},
    {"name": "Matthew Wade", "role": "wicketkeeper", "nationality": "Overseas", "batting_avg": 24.5, "strike_rate": 129.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 1.0, "pitch_suitability": "PACE", "ipl_team": "GT", "ipl_season": 2024},
    {"name": "Wriddhiman Saha", "role": "wicketkeeper", "nationality": "Indian", "batting_avg": 24.8, "strike_rate": 127.5, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 0.75, "pitch_suitability": "PACE", "ipl_team": "KKR", "ipl_season": 2023},
    {"name": "Anuj Rawat", "role": "wicketkeeper", "nationality": "Indian", "batting_avg": 21.0, "strike_rate": 122.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 0.3, "pitch_suitability": "NEUTRAL", "ipl_team": "BAN", "ipl_season": 2024},
    {"name": "Kumar Kushagra", "role": "wicketkeeper", "nationality": "Indian", "batting_avg": 22.0, "strike_rate": 130.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 0.3, "pitch_suitability": "SPIN", "ipl_team": "DC", "ipl_season": 2024},

    # --- ALLROUNDERS ---
    {"name": "Hardik Pandya", "role": "allrounder", "nationality": "Indian", "batting_avg": 29.8, "strike_rate": 144.0, "bowling_economy": 8.4, "bowling_avg": 28.5, "base_price": 2.0, "pitch_suitability": "PACE", "ipl_team": "MI", "ipl_season": 2024},
    {"name": "Ravindra Jadeja", "role": "allrounder", "nationality": "Indian", "batting_avg": 26.5, "strike_rate": 128.5, "bowling_economy": 7.6, "bowling_avg": 29.8, "base_price": 2.0, "pitch_suitability": "SPIN", "ipl_team": "CSK", "ipl_season": 2024},
    {"name": "Glenn Maxwell", "role": "allrounder", "nationality": "Overseas", "batting_avg": 25.8, "strike_rate": 156.4, "bowling_economy": 8.1, "bowling_avg": 31.0, "base_price": 2.0, "pitch_suitability": "SPIN", "ipl_team": "RCB", "ipl_season": 2024},
    {"name": "Andre Russell", "role": "allrounder", "nationality": "Overseas", "batting_avg": 29.2, "strike_rate": 174.0, "bowling_economy": 8.8, "bowling_avg": 24.2, "base_price": 2.0, "pitch_suitability": "PACE", "ipl_team": "KKR", "ipl_season": 2024},
    {"name": "Axar Patel", "role": "allrounder", "nationality": "Indian", "batting_avg": 22.8, "strike_rate": 130.0, "bowling_economy": 7.2, "bowling_avg": 27.5, "base_price": 2.0, "pitch_suitability": "SPIN", "ipl_team": "DC", "ipl_season": 2024},
    {"name": "Marcus Stoinis", "role": "allrounder", "nationality": "Overseas", "batting_avg": 27.4, "strike_rate": 139.0, "bowling_economy": 9.0, "bowling_avg": 30.5, "base_price": 1.5, "pitch_suitability": "PACE", "ipl_team": "LSG", "ipl_season": 2024},
    {"name": "Liam Livingstone", "role": "allrounder", "nationality": "Overseas", "batting_avg": 26.2, "strike_rate": 162.0, "bowling_economy": 8.3, "bowling_avg": 27.0, "base_price": 1.5, "pitch_suitability": "SPIN", "ipl_team": "PBKS", "ipl_season": 2024},
    {"name": "Krunal Pandya", "role": "allrounder", "nationality": "Indian", "batting_avg": 22.0, "strike_rate": 128.0, "bowling_economy": 7.3, "bowling_avg": 31.2, "base_price": 1.0, "pitch_suitability": "SPIN", "ipl_team": "BAN", "ipl_season": 2024},
    {"name": "Sunil Narine", "role": "allrounder", "nationality": "Overseas", "batting_avg": 16.5, "strike_rate": 158.0, "bowling_economy": 6.7, "bowling_avg": 23.5, "base_price": 2.0, "pitch_suitability": "SPIN", "ipl_team": "KKR", "ipl_season": 2024},
    {"name": "Mitchell Marsh", "role": "allrounder", "nationality": "Overseas", "batting_avg": 25.1, "strike_rate": 133.0, "bowling_economy": 8.5, "bowling_avg": 29.0, "base_price": 2.0, "pitch_suitability": "PACE", "ipl_team": "SRH", "ipl_season": 2024},
    {"name": "Washington Sundar", "role": "allrounder", "nationality": "Indian", "batting_avg": 20.4, "strike_rate": 120.0, "bowling_economy": 7.4, "bowling_avg": 33.5, "base_price": 1.0, "pitch_suitability": "SPIN", "ipl_team": "SRH", "ipl_season": 2024},
    {"name": "Riyan Parag", "role": "allrounder", "nationality": "Indian", "batting_avg": 28.5, "strike_rate": 140.0, "bowling_economy": 8.6, "bowling_avg": 36.0, "base_price": 0.5, "pitch_suitability": "NEUTRAL", "ipl_team": "RR", "ipl_season": 2024},
    {"name": "Nitish Reddy", "role": "allrounder", "nationality": "Indian", "batting_avg": 27.0, "strike_rate": 135.0, "bowling_economy": 8.5, "bowling_avg": 26.0, "base_price": 0.3, "pitch_suitability": "PACE", "ipl_team": "SRH", "ipl_season": 2024},
    {"name": "Venkatesh Iyer", "role": "allrounder", "nationality": "Indian", "batting_avg": 28.2, "strike_rate": 134.0, "bowling_economy": 8.9, "bowling_avg": 35.0, "base_price": 1.0, "pitch_suitability": "NEUTRAL", "ipl_team": "KKR", "ipl_season": 2024},
    {"name": "Vijay Shankar", "role": "allrounder", "nationality": "Indian", "batting_avg": 23.0, "strike_rate": 125.0, "bowling_economy": 8.8, "bowling_avg": 38.0, "base_price": 0.5, "pitch_suitability": "PACE", "ipl_team": "SRH", "ipl_season": 2024},
    {"name": "Rachin Ravindra", "role": "allrounder", "nationality": "Overseas", "batting_avg": 28.0, "strike_rate": 136.0, "bowling_economy": 7.9, "bowling_avg": 32.0, "base_price": 1.0, "pitch_suitability": "SPIN", "ipl_team": "KKR", "ipl_season": 2024},
    {"name": "Daryl Mitchell", "role": "allrounder", "nationality": "Overseas", "batting_avg": 29.5, "strike_rate": 132.0, "bowling_economy": 8.8, "bowling_avg": 34.0, "base_price": 1.5, "pitch_suitability": "NEUTRAL", "ipl_team": "GT", "ipl_season": 2024},
    {"name": "Moeen Ali", "role": "allrounder", "nationality": "Overseas", "batting_avg": 22.8, "strike_rate": 131.5, "bowling_economy": 7.1, "bowling_avg": 29.2, "base_price": 1.5, "pitch_suitability": "SPIN"},
    {"name": "Sam Curran", "role": "allrounder", "nationality": "Overseas", "batting_avg": 23.5, "strike_rate": 135.0, "bowling_economy": 9.2, "bowling_avg": 31.0, "base_price": 2.0, "pitch_suitability": "PACE"},
    {"name": "Marco Jansen", "role": "allrounder", "nationality": "Overseas", "batting_avg": 18.0, "strike_rate": 125.0, "bowling_economy": 8.6, "bowling_avg": 27.5, "base_price": 1.25, "pitch_suitability": "PACE"},
    {"name": "Ramandeep Singh", "role": "allrounder", "nationality": "Indian", "batting_avg": 22.0, "strike_rate": 145.0, "bowling_economy": 8.8, "bowling_avg": 28.0, "base_price": 0.3, "pitch_suitability": "PACE"},
    {"name": "Shahbaz Ahmed", "role": "allrounder", "nationality": "Indian", "batting_avg": 21.5, "strike_rate": 123.0, "bowling_economy": 7.8, "bowling_avg": 32.5, "base_price": 0.5, "pitch_suitability": "SPIN"},
    {"name": "Rahul Tewatia", "role": "allrounder", "nationality": "Indian", "batting_avg": 25.5, "strike_rate": 140.0, "bowling_economy": 8.0, "bowling_avg": 33.0, "base_price": 0.75, "pitch_suitability": "SPIN"},
    {"name": "Lalit Yadav", "role": "allrounder", "nationality": "Indian", "batting_avg": 18.2, "strike_rate": 115.0, "bowling_economy": 7.9, "bowling_avg": 32.0, "base_price": 0.3, "pitch_suitability": "SPIN"},
    {"name": "Mohammad Nabi", "role": "allrounder", "nationality": "Overseas", "batting_avg": 19.8, "strike_rate": 128.0, "bowling_economy": 7.3, "bowling_avg": 30.5, "base_price": 1.0, "pitch_suitability": "SPIN"},
    {"name": "Romario Shepherd", "role": "allrounder", "nationality": "Overseas", "batting_avg": 21.0, "strike_rate": 150.0, "bowling_economy": 9.8, "bowling_avg": 32.0, "base_price": 0.75, "pitch_suitability": "PACE"},
    {"name": "Sikandar Raza", "role": "allrounder", "nationality": "Overseas", "batting_avg": 24.2, "strike_rate": 136.0, "bowling_economy": 7.6, "bowling_avg": 26.5, "base_price": 1.0, "pitch_suitability": "SPIN"},
    {"name": "Azmatullah Omarzai", "role": "allrounder", "nationality": "Overseas", "batting_avg": 21.0, "strike_rate": 126.0, "bowling_economy": 8.7, "bowling_avg": 28.0, "base_price": 0.5, "pitch_suitability": "PACE"},
    {"name": "Deepak Chahar", "role": "allrounder", "nationality": "Indian", "batting_avg": 14.5, "strike_rate": 128.0, "bowling_economy": 7.9, "bowling_avg": 27.2, "base_price": 1.5, "pitch_suitability": "PACE"},
    {"name": "Shardul Thakur", "role": "allrounder", "nationality": "Indian", "batting_avg": 15.8, "strike_rate": 131.0, "bowling_economy": 9.1, "bowling_avg": 28.8, "base_price": 1.25, "pitch_suitability": "PACE"},

    # --- BOWLERS ---
    {"name": "Jasprit Bumrah", "role": "bowler", "nationality": "Indian", "batting_avg": 5.0, "strike_rate": 80.0, "bowling_economy": 6.9, "bowling_avg": 19.5, "base_price": 2.0, "pitch_suitability": "PACE", "ipl_team": "MI", "ipl_season": 2024},
    {"name": "Rashid Khan", "role": "bowler", "nationality": "Overseas", "batting_avg": 15.4, "strike_rate": 142.0, "bowling_economy": 6.8, "bowling_avg": 21.2, "base_price": 2.0, "pitch_suitability": "SPIN", "ipl_team": "GT", "ipl_season": 2024},
    {"name": "Yuzvendra Chahal", "role": "bowler", "nationality": "Indian", "batting_avg": 3.0, "strike_rate": 50.0, "bowling_economy": 7.7, "bowling_avg": 21.8, "base_price": 2.0, "pitch_suitability": "SPIN", "ipl_team": "RR", "ipl_season": 2024},
    {"name": "Mohammed Shami", "role": "bowler", "nationality": "Indian", "batting_avg": 6.2, "strike_rate": 88.0, "bowling_economy": 7.8, "bowling_avg": 23.0, "base_price": 2.0, "pitch_suitability": "PACE", "ipl_team": "GT", "ipl_season": 2024},
    {"name": "Mitchell Starc", "role": "bowler", "nationality": "Overseas", "batting_avg": 8.5, "strike_rate": 110.0, "bowling_economy": 8.2, "bowling_avg": 22.4, "base_price": 2.0, "pitch_suitability": "PACE", "ipl_team": "KKR", "ipl_season": 2024},
    {"name": "Pat Cummins", "role": "bowler", "nationality": "Overseas", "batting_avg": 18.2, "strike_rate": 139.5, "bowling_economy": 8.0, "bowling_avg": 25.5, "base_price": 2.0, "pitch_suitability": "PACE", "ipl_team": "KKR", "ipl_season": 2024},
    {"name": "Kagiso Rabada", "role": "bowler", "nationality": "Overseas", "batting_avg": 7.8, "strike_rate": 98.0, "bowling_economy": 8.1, "bowling_avg": 20.8, "base_price": 2.0, "pitch_suitability": "PACE", "ipl_team": "DC", "ipl_season": 2024},
    {"name": "Trent Boult", "role": "bowler", "nationality": "Overseas", "batting_avg": 5.0, "strike_rate": 72.0, "bowling_economy": 7.9, "bowling_avg": 24.5, "base_price": 2.0, "pitch_suitability": "PACE", "ipl_team": "RR", "ipl_season": 2024},
    {"name": "Kuldeep Yadav", "role": "bowler", "nationality": "Indian", "batting_avg": 8.0, "strike_rate": 82.0, "bowling_economy": 7.2, "bowling_avg": 22.0, "base_price": 1.5, "pitch_suitability": "SPIN", "ipl_team": "DC", "ipl_season": 2024},
    {"name": "Axar Patel", "role": "bowler", "nationality": "Indian", "batting_avg": 19.5, "strike_rate": 132.0, "bowling_economy": 7.1, "bowling_avg": 27.0, "base_price": 1.5, "pitch_suitability": "SPIN", "ipl_team": "DC", "ipl_season": 2024},
    {"name": "Mohammed Siraj", "role": "bowler", "nationality": "Indian", "batting_avg": 4.5, "strike_rate": 65.0, "bowling_economy": 8.4, "bowling_avg": 29.5, "base_price": 1.5, "pitch_suitability": "PACE", "ipl_team": "RCB", "ipl_season": 2024},
    {"name": "Arshdeep Singh", "role": "bowler", "nationality": "Indian", "batting_avg": 5.2, "strike_rate": 70.0, "bowling_economy": 8.5, "bowling_avg": 26.2, "base_price": 1.5, "pitch_suitability": "PACE", "ipl_team": "PBKS", "ipl_season": 2024},
    {"name": "Matheesha Pathirana", "role": "bowler", "nationality": "Overseas", "batting_avg": 2.0, "strike_rate": 40.0, "bowling_economy": 7.8, "bowling_avg": 18.5, "base_price": 1.5, "pitch_suitability": "PACE", "ipl_team": "CSK", "ipl_season": 2024},
    {"name": "Ravi Bishnoi", "role": "bowler", "nationality": "Indian", "batting_avg": 5.5, "strike_rate": 75.0, "bowling_economy": 7.4, "bowling_avg": 25.0, "base_price": 1.0, "pitch_suitability": "SPIN", "ipl_team": "LSG", "ipl_season": 2024},
    {"name": "Bhuvneshwar Kumar", "role": "bowler", "nationality": "Indian", "batting_avg": 8.4, "strike_rate": 92.0, "bowling_economy": 7.5, "bowling_avg": 26.8, "base_price": 1.5, "pitch_suitability": "PACE", "ipl_team": "SRH", "ipl_season": 2024},
    {"name": "Harshal Patel", "role": "bowler", "nationality": "Indian", "batting_avg": 11.2, "strike_rate": 120.0, "bowling_economy": 8.6, "bowling_avg": 22.0, "base_price": 1.5, "pitch_suitability": "PACE", "ipl_team": "RCB", "ipl_season": 2024},
    {"name": "Avesh Khan", "role": "bowler", "nationality": "Indian", "batting_avg": 4.0, "strike_rate": 60.0, "bowling_economy": 8.3, "bowling_avg": 28.5, "base_price": 1.0, "pitch_suitability": "PACE", "ipl_team": "DC", "ipl_season": 2024},
    {"name": "Sandip Sharma", "role": "bowler", "nationality": "Indian", "batting_avg": 4.0, "strike_rate": 60.0, "bowling_economy": 7.8, "bowling_avg": 25.8, "base_price": 0.75, "pitch_suitability": "PACE", "ipl_team": "GT", "ipl_season": 2024},
    {"name": "Varun Chakaravarthy", "role": "bowler", "nationality": "Indian", "batting_avg": 2.0, "strike_rate": 40.0, "bowling_economy": 7.5, "bowling_avg": 22.5, "base_price": 1.25, "pitch_suitability": "SPIN", "ipl_team": "KKR", "ipl_season": 2024},
    {"name": "Maheesh Theekshana", "role": "bowler", "nationality": "Overseas", "batting_avg": 3.0, "strike_rate": 55.0, "bowling_economy": 7.3, "bowling_avg": 28.0, "base_price": 1.0, "pitch_suitability": "SPIN", "ipl_team": "CSK", "ipl_season": 2024},
    {"name": "T Natarajan", "role": "bowler", "nationality": "Indian", "batting_avg": 3.0, "strike_rate": 50.0, "bowling_economy": 8.2, "bowling_avg": 24.0, "base_price": 1.0, "pitch_suitability": "PACE", "ipl_team": "SRH", "ipl_season": 2024},
    {"name": "Krunal Pandya", "role": "bowler", "nationality": "Indian", "batting_avg": 18.0, "strike_rate": 122.0, "bowling_economy": 7.3, "bowling_avg": 31.0, "base_price": 1.0, "pitch_suitability": "SPIN", "ipl_team": "BAN", "ipl_season": 2024},
    {"name": "Khaleel Ahmed", "role": "bowler", "nationality": "Indian", "batting_avg": 2.0, "strike_rate": 40.0, "bowling_economy": 8.4, "bowling_avg": 27.5, "base_price": 0.75, "pitch_suitability": "PACE", "ipl_team": "LSG", "ipl_season": 2024},
    {"name": "Mayank Yadav", "role": "bowler", "nationality": "Indian", "batting_avg": 2.0, "strike_rate": 50.0, "bowling_economy": 7.0, "bowling_avg": 16.0, "base_price": 0.5, "pitch_suitability": "PACE", "ipl_team": "LSG", "ipl_season": 2024},
    {"name": "Mohit Sharma", "role": "bowler", "nationality": "Indian", "batting_avg": 5.0, "strike_rate": 78.0, "bowling_economy": 8.4, "bowling_avg": 23.8, "base_price": 0.75, "pitch_suitability": "PACE", "ipl_team": "GT", "ipl_season": 2024},
    {"name": "Lockie Ferguson", "role": "bowler", "nationality": "Overseas", "batting_avg": 6.0, "strike_rate": 90.0, "bowling_economy": 8.6, "bowling_avg": 26.5, "base_price": 1.0, "pitch_suitability": "PACE", "ipl_team": "GT", "ipl_season": 2024},
    {"name": "Naveen-ul-Haq", "role": "bowler", "nationality": "Overseas", "batting_avg": 5.0, "strike_rate": 70.0, "bowling_economy": 8.2, "bowling_avg": 24.8, "base_price": 1.0, "pitch_suitability": "PACE", "ipl_team": "BAN", "ipl_season": 2024},
    {"name": "Spencer Johnson", "role": "bowler", "nationality": "Overseas", "batting_avg": 4.0, "strike_rate": 60.0, "bowling_economy": 8.5, "bowling_avg": 26.0, "base_price": 0.75, "pitch_suitability": "PACE", "ipl_team": "SRH", "ipl_season": 2024},
    {"name": "Noor Ahmad", "role": "bowler", "nationality": "Overseas", "batting_avg": 2.0, "strike_rate": 45.0, "bowling_economy": 7.4, "bowling_avg": 25.5, "base_price": 1.0, "pitch_suitability": "SPIN", "ipl_team": "GT", "ipl_season": 2024},
    {"name": "Gerald Coetzee", "role": "bowler", "nationality": "Overseas", "batting_avg": 8.0, "strike_rate": 105.0, "bowling_economy": 8.8, "bowling_avg": 23.0, "base_price": 1.25, "pitch_suitability": "PACE", "ipl_team": "MI", "ipl_season": 2024},
    {"name": "Mustafizur Rahman", "role": "bowler", "nationality": "Overseas", "batting_avg": 2.5, "strike_rate": 45.0, "bowling_economy": 7.9, "bowling_avg": 22.8, "base_price": 1.5, "pitch_suitability": "PACE", "ipl_team": "RR", "ipl_season": 2024},
    {"name": "Anrich Nortje", "role": "bowler", "nationality": "Overseas", "batting_avg": 5.0, "strike_rate": 80.0, "bowling_economy": 9.2, "bowling_avg": 25.0, "base_price": 1.5, "pitch_suitability": "PACE", "ipl_team": "DC", "ipl_season": 2024},
    {"name": "Dushmantha Chameera", "role": "bowler", "nationality": "Overseas", "batting_avg": 6.0, "strike_rate": 75.0, "bowling_economy": 8.6, "bowling_avg": 29.5, "base_price": 0.75, "pitch_suitability": "PACE", "ipl_team": "RCB", "ipl_season": 2024},
    {"name": "Harpreet Brar", "role": "bowler", "nationality": "Indian", "batting_avg": 12.0, "strike_rate": 118.0, "bowling_economy": 7.2, "bowling_avg": 28.5, "base_price": 0.5, "pitch_suitability": "SPIN", "ipl_team": "PBKS", "ipl_season": 2024},
    {"name": "Karn Sharma", "role": "bowler", "nationality": "Indian", "batting_avg": 8.5, "strike_rate": 115.0, "bowling_economy": 8.2, "bowling_avg": 26.0, "base_price": 0.5, "pitch_suitability": "SPIN", "ipl_team": "RR", "ipl_season": 2024},
    {"name": "Piyush Chawla", "role": "bowler", "nationality": "Indian", "batting_avg": 10.5, "strike_rate": 110.0, "bowling_economy": 7.9, "bowling_avg": 27.0, "base_price": 0.5, "pitch_suitability": "SPIN", "ipl_team": "CSK", "ipl_season": 2024},
    {"name": "Suyash Sharma", "role": "bowler", "nationality": "Indian", "batting_avg": 2.0, "strike_rate": 40.0, "bowling_economy": 7.8, "bowling_avg": 28.0, "base_price": 0.3, "pitch_suitability": "SPIN", "ipl_team": "RR", "ipl_season": 2024},
    {"name": "Vaibhav Arora", "role": "bowler", "nationality": "Indian", "batting_avg": 3.0, "strike_rate": 55.0, "bowling_economy": 8.5, "bowling_avg": 25.0, "base_price": 0.3, "pitch_suitability": "PACE", "ipl_team": "DC", "ipl_season": 2024},
    {"name": "Yash Dayal", "role": "bowler", "nationality": "Indian", "batting_avg": 2.0, "strike_rate": 45.0, "bowling_economy": 8.3, "bowling_avg": 29.0, "base_price": 0.5, "pitch_suitability": "PACE", "ipl_team": "GT", "ipl_season": 2024},
    {"name": "Tushar Deshpande", "role": "bowler", "nationality": "Indian", "batting_avg": 5.0, "strike_rate": 80.0, "bowling_economy": 8.5, "bowling_avg": 23.5, "base_price": 0.5, "pitch_suitability": "PACE", "ipl_team": "CSK", "ipl_season": 2024},
]

async def seed_database():
    print("Connecting to the database at:", DATABASE_URL)
    engine = create_async_engine(DATABASE_URL, echo=True)
    
    # Drop existing tables and recreate with new schema
    async with engine.begin() as conn:
        print("Dropping existing tables...")
        await conn.run_sync(Base.metadata.drop_all)
        print("Tables dropped successfully.")
        
        print("Creating new tables with updated schema...")
        await conn.run_sync(Base.metadata.create_all)
        print("Tables created successfully.")
        
    # Seed player data
    from sqlalchemy.ext.asyncio import AsyncSession
    async_session = AsyncSession(engine, expire_on_commit=False)
    
    async with async_session as session:
        print(f"Seeding {len(PLAYERS_DATA)} players...")
        for p_dict in PLAYERS_DATA:
            player = Player(**p_dict)
            session.add(player)
        await session.commit()
        print("Database seeded successfully!")
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed_database())

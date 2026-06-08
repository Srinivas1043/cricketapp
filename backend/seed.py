import asyncio
import os
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy.future import select
from sqlalchemy.orm import declarative_base
from backend.database import Base, DATABASE_URL
from backend.models import Player

# Make sure models are imported so metadata knows about them
import backend.models

# 120+ Real IPL Players with realistic stats
PLAYERS_DATA = [
    # --- BATSMEN ---
    {"name": "Virat Kohli", "role": "batsman", "nationality": "Indian", "batting_avg": 38.5, "strike_rate": 135.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 2.0, "pitch_suitability": "NEUTRAL"},
    {"name": "Rohit Sharma", "role": "batsman", "nationality": "Indian", "batting_avg": 30.2, "strike_rate": 133.5, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 2.0, "pitch_suitability": "PACE"},
    {"name": "Shubman Gill", "role": "batsman", "nationality": "Indian", "batting_avg": 37.8, "strike_rate": 136.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 2.0, "pitch_suitability": "NEUTRAL"},
    {"name": "Suryakumar Yadav", "role": "batsman", "nationality": "Indian", "batting_avg": 35.4, "strike_rate": 172.5, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 2.0, "pitch_suitability": "PACE"},
    {"name": "Yashasvi Jaiswal", "role": "batsman", "nationality": "Indian", "batting_avg": 32.8, "strike_rate": 145.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 1.5, "pitch_suitability": "NEUTRAL"},
    {"name": "Ruturaj Gaikwad", "role": "batsman", "nationality": "Indian", "batting_avg": 39.1, "strike_rate": 137.5, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 1.5, "pitch_suitability": "NEUTRAL"},
    {"name": "Rinku Singh", "role": "batsman", "nationality": "Indian", "batting_avg": 36.2, "strike_rate": 148.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 1.0, "pitch_suitability": "SPIN"},
    {"name": "Travis Head", "role": "batsman", "nationality": "Overseas", "batting_avg": 31.5, "strike_rate": 158.0, "bowling_economy": 8.5, "bowling_avg": 35.0, "base_price": 2.0, "pitch_suitability": "PACE"},
    {"name": "Faf du Plessis", "role": "batsman", "nationality": "Overseas", "batting_avg": 34.0, "strike_rate": 134.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 1.5, "pitch_suitability": "PACE"},
    {"name": "David Warner", "role": "batsman", "nationality": "Overseas", "batting_avg": 41.2, "strike_rate": 139.8, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 2.0, "pitch_suitability": "NEUTRAL"},
    {"name": "Kane Williamson", "role": "batsman", "nationality": "Overseas", "batting_avg": 36.0, "strike_rate": 126.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 1.5, "pitch_suitability": "SPIN"},
    {"name": "Sai Sudharsan", "role": "batsman", "nationality": "Indian", "batting_avg": 42.0, "strike_rate": 129.5, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 0.5, "pitch_suitability": "SPIN"},
    {"name": "Rajat Patidar", "role": "batsman", "nationality": "Indian", "batting_avg": 33.5, "strike_rate": 142.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 0.5, "pitch_suitability": "SPIN"},
    {"name": "Ajinkya Rahane", "role": "batsman", "nationality": "Indian", "batting_avg": 26.8, "strike_rate": 122.5, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 1.0, "pitch_suitability": "PACE"},
    {"name": "Tilak Varma", "role": "batsman", "nationality": "Indian", "batting_avg": 38.9, "strike_rate": 140.0, "bowling_economy": 8.0, "bowling_avg": 28.0, "base_price": 1.0, "pitch_suitability": "NEUTRAL"},
    {"name": "Shimron Hetmyer", "role": "batsman", "nationality": "Overseas", "batting_avg": 29.8, "strike_rate": 144.5, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 1.5, "pitch_suitability": "SPIN"},
    {"name": "Rovman Powell", "role": "batsman", "nationality": "Overseas", "batting_avg": 25.5, "strike_rate": 139.0, "bowling_economy": 9.2, "bowling_avg": 42.0, "base_price": 1.0, "pitch_suitability": "PACE"},
    {"name": "Abhishek Sharma", "role": "batsman", "nationality": "Indian", "batting_avg": 28.5, "strike_rate": 148.0, "bowling_economy": 7.8, "bowling_avg": 30.0, "base_price": 0.5, "pitch_suitability": "NEUTRAL"},
    {"name": "Mayank Agarwal", "role": "batsman", "nationality": "Indian", "batting_avg": 23.0, "strike_rate": 131.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 1.0, "pitch_suitability": "PACE"},
    {"name": "Devdutt Padikkal", "role": "batsman", "nationality": "Indian", "batting_avg": 27.2, "strike_rate": 124.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 0.75, "pitch_suitability": "NEUTRAL"},
    {"name": "Prithvi Shaw", "role": "batsman", "nationality": "Indian", "batting_avg": 24.8, "strike_rate": 146.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 0.75, "pitch_suitability": "PACE"},
    {"name": "Manish Pandey", "role": "batsman", "nationality": "Indian", "batting_avg": 29.0, "strike_rate": 121.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 0.5, "pitch_suitability": "SPIN"},
    {"name": "Shahrukh Khan", "role": "batsman", "nationality": "Indian", "batting_avg": 22.4, "strike_rate": 138.0, "bowling_economy": 8.0, "bowling_avg": 34.0, "base_price": 0.5, "pitch_suitability": "PACE"},
    {"name": "Deepak Hooda", "role": "batsman", "nationality": "Indian", "batting_avg": 19.5, "strike_rate": 128.5, "bowling_economy": 8.4, "bowling_avg": 31.0, "base_price": 0.75, "pitch_suitability": "SPIN"},
    {"name": "Karun Nair", "role": "batsman", "nationality": "Indian", "batting_avg": 24.5, "strike_rate": 128.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 0.5, "pitch_suitability": "SPIN"},
    {"name": "Tristan Stubbs", "role": "batsman", "nationality": "Overseas", "batting_avg": 33.5, "strike_rate": 155.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 1.0, "pitch_suitability": "NEUTRAL"},
    {"name": "Jake Fraser-McGurk", "role": "batsman", "nationality": "Overseas", "batting_avg": 30.0, "strike_rate": 190.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 1.0, "pitch_suitability": "PACE"},
    {"name": "Nehal Wadhera", "role": "batsman", "nationality": "Indian", "batting_avg": 28.2, "strike_rate": 139.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 0.3, "pitch_suitability": "NEUTRAL"},
    {"name": "Abdul Samad", "role": "batsman", "nationality": "Indian", "batting_avg": 20.8, "strike_rate": 141.0, "bowling_economy": 9.5, "bowling_avg": 45.0, "base_price": 0.3, "pitch_suitability": "PACE"},
    {"name": "Ayush Badoni", "role": "batsman", "nationality": "Indian", "batting_avg": 24.0, "strike_rate": 132.0, "bowling_economy": 7.5, "bowling_avg": 27.0, "base_price": 0.3, "pitch_suitability": "SPIN"},

    # --- WICKETKEEPERS ---
    {"name": "MS Dhoni", "role": "wicketkeeper", "nationality": "Indian", "batting_avg": 38.8, "strike_rate": 137.5, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 2.0, "pitch_suitability": "SPIN"},
    {"name": "Rishabh Pant", "role": "wicketkeeper", "nationality": "Indian", "batting_avg": 35.2, "strike_rate": 148.5, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 2.0, "pitch_suitability": "NEUTRAL"},
    {"name": "Sanju Samson", "role": "wicketkeeper", "nationality": "Indian", "batting_avg": 30.5, "strike_rate": 138.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 2.0, "pitch_suitability": "PACE"},
    {"name": "Heinrich Klaasen", "role": "wicketkeeper", "nationality": "Overseas", "batting_avg": 37.4, "strike_rate": 165.8, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 2.0, "pitch_suitability": "SPIN"},
    {"name": "Ishan Kishan", "role": "wicketkeeper", "nationality": "Indian", "batting_avg": 29.4, "strike_rate": 135.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 1.5, "pitch_suitability": "NEUTRAL"},
    {"name": "Nicholas Pooran", "role": "wicketkeeper", "nationality": "Overseas", "batting_avg": 32.2, "strike_rate": 156.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 2.0, "pitch_suitability": "SPIN"},
    {"name": "Quinton de Kock", "role": "wicketkeeper", "nationality": "Overseas", "batting_avg": 31.8, "strike_rate": 134.2, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 2.0, "pitch_suitability": "PACE"},
    {"name": "KL Rahul", "role": "wicketkeeper", "nationality": "Indian", "batting_avg": 45.5, "strike_rate": 130.2, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 2.0, "pitch_suitability": "NEUTRAL"},
    {"name": "Phil Salt", "role": "wicketkeeper", "nationality": "Overseas", "batting_avg": 28.5, "strike_rate": 152.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 1.5, "pitch_suitability": "PACE"},
    {"name": "Jitesh Sharma", "role": "wicketkeeper", "nationality": "Indian", "batting_avg": 23.4, "strike_rate": 142.5, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 0.75, "pitch_suitability": "NEUTRAL"},
    {"name": "Dhruv Jurel", "role": "wicketkeeper", "nationality": "Indian", "batting_avg": 28.0, "strike_rate": 136.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 0.5, "pitch_suitability": "SPIN"},
    {"name": "Matthew Wade", "role": "wicketkeeper", "nationality": "Overseas", "batting_avg": 24.5, "strike_rate": 129.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 1.0, "pitch_suitability": "PACE"},
    {"name": "Wriddhiman Saha", "role": "wicketkeeper", "nationality": "Indian", "batting_avg": 24.8, "strike_rate": 127.5, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 0.75, "pitch_suitability": "PACE"},
    {"name": "Anuj Rawat", "role": "wicketkeeper", "nationality": "Indian", "batting_avg": 21.0, "strike_rate": 122.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 0.3, "pitch_suitability": "NEUTRAL"},
    {"name": "Kumar Kushagra", "role": "wicketkeeper", "nationality": "Indian", "batting_avg": 22.0, "strike_rate": 130.0, "bowling_economy": 0.0, "bowling_avg": 0.0, "base_price": 0.3, "pitch_suitability": "SPIN"},

    # --- ALLROUNDERS ---
    {"name": "Hardik Pandya", "role": "allrounder", "nationality": "Indian", "batting_avg": 29.8, "strike_rate": 144.0, "bowling_economy": 8.4, "bowling_avg": 28.5, "base_price": 2.0, "pitch_suitability": "PACE"},
    {"name": "Ravindra Jadeja", "role": "allrounder", "nationality": "Indian", "batting_avg": 26.5, "strike_rate": 128.5, "bowling_economy": 7.6, "bowling_avg": 29.8, "base_price": 2.0, "pitch_suitability": "SPIN"},
    {"name": "Glenn Maxwell", "role": "allrounder", "nationality": "Overseas", "batting_avg": 25.8, "strike_rate": 156.4, "bowling_economy": 8.1, "bowling_avg": 31.0, "base_price": 2.0, "pitch_suitability": "SPIN"},
    {"name": "Andre Russell", "role": "allrounder", "nationality": "Overseas", "batting_avg": 29.2, "strike_rate": 174.0, "bowling_economy": 8.8, "bowling_avg": 24.2, "base_price": 2.0, "pitch_suitability": "PACE"},
    {"name": "Axar Patel", "role": "allrounder", "nationality": "Indian", "batting_avg": 22.8, "strike_rate": 130.0, "bowling_economy": 7.2, "bowling_avg": 27.5, "base_price": 2.0, "pitch_suitability": "SPIN"},
    {"name": "Marcus Stoinis", "role": "allrounder", "nationality": "Overseas", "batting_avg": 27.4, "strike_rate": 139.0, "bowling_economy": 9.0, "bowling_avg": 30.5, "base_price": 1.5, "pitch_suitability": "PACE"},
    {"name": "Liam Livingstone", "role": "allrounder", "nationality": "Overseas", "batting_avg": 26.2, "strike_rate": 162.0, "bowling_economy": 8.3, "bowling_avg": 27.0, "base_price": 1.5, "pitch_suitability": "SPIN"},
    {"name": "Krunal Pandya", "role": "allrounder", "nationality": "Indian", "batting_avg": 22.0, "strike_rate": 128.0, "bowling_economy": 7.3, "bowling_avg": 31.2, "base_price": 1.0, "pitch_suitability": "SPIN"},
    {"name": "Sunil Narine", "role": "allrounder", "nationality": "Overseas", "batting_avg": 16.5, "strike_rate": 158.0, "bowling_economy": 6.7, "bowling_avg": 23.5, "base_price": 2.0, "pitch_suitability": "SPIN"},
    {"name": "Mitchell Marsh", "role": "allrounder", "nationality": "Overseas", "batting_avg": 25.1, "strike_rate": 133.0, "bowling_economy": 8.5, "bowling_avg": 29.0, "base_price": 2.0, "pitch_suitability": "PACE"},
    {"name": "Washington Sundar", "role": "allrounder", "nationality": "Indian", "batting_avg": 20.4, "strike_rate": 120.0, "bowling_economy": 7.4, "bowling_avg": 33.5, "base_price": 1.0, "pitch_suitability": "SPIN"},
    {"name": "Riyan Parag", "role": "allrounder", "nationality": "Indian", "batting_avg": 28.5, "strike_rate": 140.0, "bowling_economy": 8.6, "bowling_avg": 36.0, "base_price": 0.5, "pitch_suitability": "NEUTRAL"},
    {"name": "Nitish Reddy", "role": "allrounder", "nationality": "Indian", "batting_avg": 27.0, "strike_rate": 135.0, "bowling_economy": 8.5, "bowling_avg": 26.0, "base_price": 0.3, "pitch_suitability": "PACE"},
    {"name": "Venkatesh Iyer", "role": "allrounder", "nationality": "Indian", "batting_avg": 28.2, "strike_rate": 134.0, "bowling_economy": 8.9, "bowling_avg": 35.0, "base_price": 1.0, "pitch_suitability": "NEUTRAL"},
    {"name": "Vijay Shankar", "role": "allrounder", "nationality": "Indian", "batting_avg": 23.0, "strike_rate": 125.0, "bowling_economy": 8.8, "bowling_avg": 38.0, "base_price": 0.5, "pitch_suitability": "PACE"},
    {"name": "Rachin Ravindra", "role": "allrounder", "nationality": "Overseas", "batting_avg": 28.0, "strike_rate": 136.0, "bowling_economy": 7.9, "bowling_avg": 32.0, "base_price": 1.0, "pitch_suitability": "SPIN"},
    {"name": "Daryl Mitchell", "role": "allrounder", "nationality": "Overseas", "batting_avg": 29.5, "strike_rate": 132.0, "bowling_economy": 8.8, "bowling_avg": 34.0, "base_price": 1.5, "pitch_suitability": "NEUTRAL"},
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
    {"name": "Jasprit Bumrah", "role": "bowler", "nationality": "Indian", "batting_avg": 5.0, "strike_rate": 80.0, "bowling_economy": 6.9, "bowling_avg": 19.5, "base_price": 2.0, "pitch_suitability": "PACE"},
    {"name": "Rashid Khan", "role": "bowler", "nationality": "Overseas", "batting_avg": 15.4, "strike_rate": 142.0, "bowling_economy": 6.8, "bowling_avg": 21.2, "base_price": 2.0, "pitch_suitability": "SPIN"},
    {"name": "Yuzvendra Chahal", "role": "bowler", "nationality": "Indian", "batting_avg": 3.0, "strike_rate": 50.0, "bowling_economy": 7.7, "bowling_avg": 21.8, "base_price": 2.0, "pitch_suitability": "SPIN"},
    {"name": "Mohammed Shami", "role": "bowler", "nationality": "Indian", "batting_avg": 6.2, "strike_rate": 88.0, "bowling_economy": 7.8, "bowling_avg": 23.0, "base_price": 2.0, "pitch_suitability": "PACE"},
    {"name": "Mitchell Starc", "role": "bowler", "nationality": "Overseas", "batting_avg": 8.5, "strike_rate": 110.0, "bowling_economy": 8.2, "bowling_avg": 22.4, "base_price": 2.0, "pitch_suitability": "PACE"},
    {"name": "Pat Cummins", "role": "bowler", "nationality": "Overseas", "batting_avg": 18.2, "strike_rate": 139.5, "bowling_economy": 8.0, "bowling_avg": 25.5, "base_price": 2.0, "pitch_suitability": "PACE"},
    {"name": "Kagiso Rabada", "role": "bowler", "nationality": "Overseas", "batting_avg": 7.8, "strike_rate": 98.0, "bowling_economy": 8.1, "bowling_avg": 20.8, "base_price": 2.0, "pitch_suitability": "PACE"},
    {"name": "Trent Boult", "role": "bowler", "nationality": "Overseas", "batting_avg": 5.0, "strike_rate": 72.0, "bowling_economy": 7.9, "bowling_avg": 24.5, "base_price": 2.0, "pitch_suitability": "PACE"},
    {"name": "Kuldeep Yadav", "role": "bowler", "nationality": "Indian", "batting_avg": 8.0, "strike_rate": 82.0, "bowling_economy": 7.2, "bowling_avg": 22.0, "base_price": 1.5, "pitch_suitability": "SPIN"},
    {"name": "Axar Patel", "role": "bowler", "nationality": "Indian", "batting_avg": 19.5, "strike_rate": 132.0, "bowling_economy": 7.1, "bowling_avg": 27.0, "base_price": 1.5, "pitch_suitability": "SPIN"},
    {"name": "Mohammed Siraj", "role": "bowler", "nationality": "Indian", "batting_avg": 4.5, "strike_rate": 65.0, "bowling_economy": 8.4, "bowling_avg": 29.5, "base_price": 1.5, "pitch_suitability": "PACE"},
    {"name": "Arshdeep Singh", "role": "bowler", "nationality": "Indian", "batting_avg": 5.2, "strike_rate": 70.0, "bowling_economy": 8.5, "bowling_avg": 26.2, "base_price": 1.5, "pitch_suitability": "PACE"},
    {"name": "Matheesha Pathirana", "role": "bowler", "nationality": "Overseas", "batting_avg": 2.0, "strike_rate": 40.0, "bowling_economy": 7.8, "bowling_avg": 18.5, "base_price": 1.5, "pitch_suitability": "PACE"},
    {"name": "Ravi Bishnoi", "role": "bowler", "nationality": "Indian", "batting_avg": 5.5, "strike_rate": 75.0, "bowling_economy": 7.4, "bowling_avg": 25.0, "base_price": 1.0, "pitch_suitability": "SPIN"},
    {"name": "Bhuvneshwar Kumar", "role": "bowler", "nationality": "Indian", "batting_avg": 8.4, "strike_rate": 92.0, "bowling_economy": 7.5, "bowling_avg": 26.8, "base_price": 1.5, "pitch_suitability": "PACE"},
    {"name": "Harshal Patel", "role": "bowler", "nationality": "Indian", "batting_avg": 11.2, "strike_rate": 120.0, "bowling_economy": 8.6, "bowling_avg": 22.0, "base_price": 1.5, "pitch_suitability": "PACE"},
    {"name": "Avesh Khan", "role": "bowler", "nationality": "Indian", "batting_avg": 4.0, "strike_rate": 60.0, "bowling_economy": 8.3, "bowling_avg": 28.5, "base_price": 1.0, "pitch_suitability": "PACE"},
    {"name": "Sandip Sharma", "role": "bowler", "nationality": "Indian", "batting_avg": 4.0, "strike_rate": 60.0, "bowling_economy": 7.8, "bowling_avg": 25.8, "base_price": 0.75, "pitch_suitability": "PACE"},
    {"name": "Varun Chakaravarthy", "role": "bowler", "nationality": "Indian", "batting_avg": 2.0, "strike_rate": 40.0, "bowling_economy": 7.5, "bowling_avg": 22.5, "base_price": 1.25, "pitch_suitability": "SPIN"},
    {"name": "Maheesh Theekshana", "role": "bowler", "nationality": "Overseas", "batting_avg": 3.0, "strike_rate": 55.0, "bowling_economy": 7.3, "bowling_avg": 28.0, "base_price": 1.0, "pitch_suitability": "SPIN"},
    {"name": "T Natarajan", "role": "bowler", "nationality": "Indian", "batting_avg": 3.0, "strike_rate": 50.0, "bowling_economy": 8.2, "bowling_avg": 24.0, "base_price": 1.0, "pitch_suitability": "PACE"},
    {"name": "Krunal Pandya", "role": "bowler", "nationality": "Indian", "batting_avg": 18.0, "strike_rate": 122.0, "bowling_economy": 7.3, "bowling_avg": 31.0, "base_price": 1.0, "pitch_suitability": "SPIN"},
    {"name": "Khaleel Ahmed", "role": "bowler", "nationality": "Indian", "batting_avg": 2.0, "strike_rate": 40.0, "bowling_economy": 8.4, "bowling_avg": 27.5, "base_price": 0.75, "pitch_suitability": "PACE"},
    {"name": "Mayank Yadav", "role": "bowler", "nationality": "Indian", "batting_avg": 2.0, "strike_rate": 50.0, "bowling_economy": 7.0, "bowling_avg": 16.0, "base_price": 0.5, "pitch_suitability": "PACE"},
    {"name": "Mohit Sharma", "role": "bowler", "nationality": "Indian", "batting_avg": 5.0, "strike_rate": 78.0, "bowling_economy": 8.4, "bowling_avg": 23.8, "base_price": 0.75, "pitch_suitability": "PACE"},
    {"name": "Lockie Ferguson", "role": "bowler", "nationality": "Overseas", "batting_avg": 6.0, "strike_rate": 90.0, "bowling_economy": 8.6, "bowling_avg": 26.5, "base_price": 1.0, "pitch_suitability": "PACE"},
    {"name": "Naveen-ul-Haq", "role": "bowler", "nationality": "Overseas", "batting_avg": 5.0, "strike_rate": 70.0, "bowling_economy": 8.2, "bowling_avg": 24.8, "base_price": 1.0, "pitch_suitability": "PACE"},
    {"name": "Spencer Johnson", "role": "bowler", "nationality": "Overseas", "batting_avg": 4.0, "strike_rate": 60.0, "bowling_economy": 8.5, "bowling_avg": 26.0, "base_price": 0.75, "pitch_suitability": "PACE"},
    {"name": "Noor Ahmad", "role": "bowler", "nationality": "Overseas", "batting_avg": 2.0, "strike_rate": 45.0, "bowling_economy": 7.4, "bowling_avg": 25.5, "base_price": 1.0, "pitch_suitability": "SPIN"},
    {"name": "Gerald Coetzee", "role": "bowler", "nationality": "Overseas", "batting_avg": 8.0, "strike_rate": 105.0, "bowling_economy": 8.8, "bowling_avg": 23.0, "base_price": 1.25, "pitch_suitability": "PACE"},
    {"name": "Mustafizur Rahman", "role": "bowler", "nationality": "Overseas", "batting_avg": 2.5, "strike_rate": 45.0, "bowling_economy": 7.9, "bowling_avg": 22.8, "base_price": 1.5, "pitch_suitability": "PACE"},
    {"name": "Anrich Nortje", "role": "bowler", "nationality": "Overseas", "batting_avg": 5.0, "strike_rate": 80.0, "bowling_economy": 9.2, "bowling_avg": 25.0, "base_price": 1.5, "pitch_suitability": "PACE"},
    {"name": "Dushmantha Chameera", "role": "bowler", "nationality": "Overseas", "batting_avg": 6.0, "strike_rate": 75.0, "bowling_economy": 8.6, "bowling_avg": 29.5, "base_price": 0.75, "pitch_suitability": "PACE"},
    {"name": "Harpreet Brar", "role": "bowler", "nationality": "Indian", "batting_avg": 12.0, "strike_rate": 118.0, "bowling_economy": 7.2, "bowling_avg": 28.5, "base_price": 0.5, "pitch_suitability": "SPIN"},
    {"name": "Karn Sharma", "role": "bowler", "nationality": "Indian", "batting_avg": 8.5, "strike_rate": 115.0, "bowling_economy": 8.2, "bowling_avg": 26.0, "base_price": 0.5, "pitch_suitability": "SPIN"},
    {"name": "Piyush Chawla", "role": "bowler", "nationality": "Indian", "batting_avg": 10.5, "strike_rate": 110.0, "bowling_economy": 7.9, "bowling_avg": 27.0, "base_price": 0.5, "pitch_suitability": "SPIN"},
    {"name": "Suyash Sharma", "role": "bowler", "nationality": "Indian", "batting_avg": 2.0, "strike_rate": 40.0, "bowling_economy": 7.8, "bowling_avg": 28.0, "base_price": 0.3, "pitch_suitability": "SPIN"},
    {"name": "Vaibhav Arora", "role": "bowler", "nationality": "Indian", "batting_avg": 3.0, "strike_rate": 55.0, "bowling_economy": 8.5, "bowling_avg": 25.0, "base_price": 0.3, "pitch_suitability": "PACE"},
    {"name": "Yash Dayal", "role": "bowler", "nationality": "Indian", "batting_avg": 2.0, "strike_rate": 45.0, "bowling_economy": 8.3, "bowling_avg": 29.0, "base_price": 0.5, "pitch_suitability": "PACE"},
    {"name": "Tushar Deshpande", "role": "bowler", "nationality": "Indian", "batting_avg": 5.0, "strike_rate": 80.0, "bowling_economy": 8.5, "bowling_avg": 23.5, "base_price": 0.5, "pitch_suitability": "PACE"},
]

async def seed_database():
    print("Connecting to the database at:", DATABASE_URL)
    engine = create_async_engine(DATABASE_URL, echo=True)
    
    # Initialize the database schema
    async with engine.begin() as conn:
        print("Creating tables...")
        await conn.run_sync(Base.metadata.create_all)
        print("Tables created successfully.")
        
    # Seed player data if table is empty
    from sqlalchemy.ext.asyncio import AsyncSession
    async_session = AsyncSession(engine, expire_on_commit=False)
    
    async with async_session as session:
        # Check if players are already seeded
        result = await session.execute(select(Player))
        existing_players = result.scalars().all()
        
        if len(existing_players) == 0:
            print(f"Seeding {len(PLAYERS_DATA)} players...")
            for p_dict in PLAYERS_DATA:
                player = Player(**p_dict)
                session.add(player)
            await session.commit()
            print("Database seeded successfully!")
        else:
            print(f"Database already contains {len(existing_players)} players. Skipping seeding.")
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(seed_database())

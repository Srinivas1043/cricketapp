import os
import random

# Iconic historical players
NAMES = [
    # CSK
    ("Suresh Raina", "batsman", "Indian", "CSK"), ("Matthew Hayden", "batsman", "Overseas", "CSK"),
    ("Michael Hussey", "batsman", "Overseas", "CSK"), ("Murali Vijay", "batsman", "Indian", "CSK"),
    ("Albie Morkel", "allrounder", "Overseas", "CSK"), ("Dwayne Bravo", "allrounder", "Overseas", "CSK"),
    ("Doug Bollinger", "bowler", "Overseas", "CSK"), ("Mohit Sharma", "bowler", "Indian", "CSK"),
    ("Ashish Nehra", "bowler", "Indian", "CSK"), ("Laxmipathy Balaji", "bowler", "Indian", "CSK"),
    # MI
    ("Sachin Tendulkar", "batsman", "Indian", "MI"), ("Sanath Jayasuriya", "allrounder", "Overseas", "MI"),
    ("Kieron Pollard", "allrounder", "Overseas", "MI"), ("Lasith Malinga", "bowler", "Overseas", "MI"),
    ("Harbhajan Singh", "bowler", "Indian", "MI"), ("Mitchell McClenaghan", "bowler", "Overseas", "MI"),
    ("Lendl Simmons", "batsman", "Overseas", "MI"), ("Corey Anderson", "allrounder", "Overseas", "MI"),
    # RCB
    ("Chris Gayle", "batsman", "Overseas", "RCB"), ("AB de Villiers", "batsman", "Overseas", "RCB"),
    ("Jacques Kallis", "allrounder", "Overseas", "RCB"), ("Zaheer Khan", "bowler", "Indian", "RCB"),
    ("Anil Kumble", "bowler", "Indian", "RCB"), ("Yuzvendra Chahal", "bowler", "Indian", "RCB"),
    ("Mitchell Starc", "bowler", "Overseas", "RCB"), ("Samuel Badree", "bowler", "Overseas", "RCB"),
    # KKR
    ("Gautam Gambhir", "batsman", "Indian", "KKR"), ("Robin Uthappa", "wicketkeeper", "Indian", "KKR"),
    ("Yusuf Pathan", "allrounder", "Indian", "KKR"), ("Sunil Narine", "allrounder", "Overseas", "KKR"),
    ("Andre Russell", "allrounder", "Overseas", "KKR"), ("Shakib Al Hasan", "allrounder", "Overseas", "KKR"),
    ("Morne Morkel", "bowler", "Overseas", "KKR"), ("Brett Lee", "bowler", "Overseas", "KKR"),
    # RR
    ("Shane Warne", "bowler", "Overseas", "RR"), ("Shane Watson", "allrounder", "Overseas", "RR"),
    ("Yusuf Pathan", "allrounder", "Indian", "RR"), ("Sohail Tanvir", "bowler", "Overseas", "RR"),
    ("Rahul Dravid", "batsman", "Indian", "RR"), ("Ajinkya Rahane", "batsman", "Indian", "RR"),
    ("Steven Smith", "batsman", "Overseas", "RR"), ("James Faulkner", "allrounder", "Overseas", "RR"),
    # SRH / DC
    ("David Warner", "batsman", "Overseas", "SRH"), ("Shikhar Dhawan", "batsman", "Indian", "SRH"),
    ("Kane Williamson", "batsman", "Overseas", "SRH"), ("Rashid Khan", "bowler", "Overseas", "SRH"),
    ("Bhuvneshwar Kumar", "bowler", "Indian", "SRH"), ("Mustafizur Rahman", "bowler", "Overseas", "SRH"),
    ("Adam Gilchrist", "wicketkeeper", "Overseas", "DC"), ("Andrew Symonds", "allrounder", "Overseas", "DC"),
    # PBKS
    ("Shaun Marsh", "batsman", "Overseas", "PBKS"), ("Virender Sehwag", "batsman", "Indian", "PBKS"),
    ("Glenn Maxwell", "allrounder", "Overseas", "PBKS"), ("David Miller", "batsman", "Overseas", "PBKS"),
    ("Sandeep Sharma", "bowler", "Indian", "PBKS"), ("Axar Patel", "allrounder", "Indian", "PBKS"),
    ("Piyush Chawla", "bowler", "Indian", "PBKS"), ("Hashim Amla", "batsman", "Overseas", "PBKS"),
]

# Expand list by duplicating them across multiple random historical years (2008 to 2023)
generated_players = []

def get_stats(role):
    if role == "batsman":
        return round(random.uniform(25.0, 45.0), 1), round(random.uniform(120.0, 160.0), 1), 0.0, 0.0
    elif role == "bowler":
        return round(random.uniform(5.0, 15.0), 1), round(random.uniform(80.0, 110.0), 1), round(random.uniform(6.5, 9.0), 1), round(random.uniform(18.0, 30.0), 1)
    elif role == "allrounder":
        return round(random.uniform(20.0, 35.0), 1), round(random.uniform(130.0, 165.0), 1), round(random.uniform(7.5, 9.5), 1), round(random.uniform(22.0, 35.0), 1)
    else: # wicketkeeper
        return round(random.uniform(22.0, 38.0), 1), round(random.uniform(125.0, 150.0), 1), 0.0, 0.0

for name, role, nat, team in NAMES:
    # Give them 3-5 historical seasons
    num_seasons = random.randint(3, 5)
    seasons = random.sample(range(2008, 2024), num_seasons)
    
    for s in seasons:
        b_avg, sr, econ, bowl_avg = get_stats(role)
        price = round(random.uniform(0.5, 3.5), 2)
        pitch = random.choice(["PACE", "SPIN", "NEUTRAL"])
        
        player_dict = f'    {{"name": "{name}", "role": "{role}", "nationality": "{nat}", "batting_avg": {b_avg}, "strike_rate": {sr}, "bowling_economy": {econ}, "bowling_avg": {bowl_avg}, "base_price": {price}, "pitch_suitability": "{pitch}", "ipl_team": "{team}", "ipl_season": {s}}},'
        generated_players.append(player_dict)

# In order to add these to seed.py, we will read seed.py, find the end of PLAYERS_DATA array, and insert them
seed_path = os.path.join(os.path.dirname(__file__), "seed.py")
with open(seed_path, "r", encoding="utf-8") as f:
    lines = f.readlines()

output_lines = []
for line in lines:
    output_lines.append(line)
    if line.strip() == "# --- BOWLERS ---":
        # Insert all generated players right before the bowlers section
        output_lines.append("    # --- HISTORICAL GENERATED --- \\n")
        output_lines.extend([p + "\\n" for p in generated_players])

with open(seed_path, "w", encoding="utf-8") as f:
    f.writelines(output_lines)

print(f"Successfully added {len(generated_players)} historical players to seed.py")

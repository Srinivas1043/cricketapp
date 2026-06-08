import asyncio
import json
import logging
import random
import string
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Set

from fastapi import FastAPI, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.database import get_db, Base
from backend.models import Room, Team, Player, RoomPlayer, Match, RoomAuctionState
from backend.schemas import (
    RoomCreate, RoomJoin, RoomResponse, TeamResponse, MatchResponse, 
    MatchSetupRequest, MatchDecisionRequest, BidRequest
)
from backend.engine.auction import AuctionManager, get_bid_increment
from backend.engine.match import MatchSimulator
from backend.engine.tournament import generate_round_robin_fixtures, recalculate_standings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("IPL_Dugout_Dynasty")

app = FastAPI(title="IPL Dugout Dynasty Backend")

# Enable CORS for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # In development, allow all origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Standard IPL Teams
DEFAULT_TEAMS = [
    {"name": "Chennai Super Kings", "short_name": "CSK", "home_ground": "M. A. Chidambaram Stadium"},
    {"name": "Mumbai Indians", "short_name": "MI", "home_ground": "Wankhede Stadium"},
    {"name": "Royal Challengers Bengaluru", "short_name": "RCB", "home_ground": "M. Chinnaswamy Stadium"},
    {"name": "Kolkata Knight Riders", "short_name": "KKR", "home_ground": "Eden Gardens"},
    {"name": "Rajasthan Royals", "short_name": "RR", "home_ground": "Sawai Mansingh Stadium"},
    {"name": "Delhi Capitals", "short_name": "DC", "home_ground": "Arun Jaitley Stadium"},
    {"name": "Sunrisers Hyderabad", "short_name": "SRH", "home_ground": "Rajiv Gandhi Intl Stadium"},
    {"name": "Lucknow Super Giants", "short_name": "LSG", "home_ground": "Ekana Cricket Stadium"},
    {"name": "Gujarat Titans", "short_name": "GT", "home_ground": "Narendra Modi Stadium"},
    {"name": "Punjab Kings", "short_name": "PBKS", "home_ground": "PCA Stadium"}
]

# --- WEBSOCKET CONNECTION MANAGER ---
class ConnectionManager:
    def __init__(self):
        # Maps room_code -> list of active websockets
        self.active_connections: Dict[str, Set[WebSocket]] = {}
        # Maps room_code -> dict of user_id -> username
        self.room_users: Dict[str, Dict[str, str]] = {}

    async def connect(self, room_code: str, websocket: WebSocket, username: str):
        await websocket.accept()
        if room_code not in self.active_connections:
            self.active_connections[room_code] = set()
        self.active_connections[room_code].add(websocket)
        logger.info(f"User {username} connected to room {room_code}")

    def disconnect(self, room_code: str, websocket: WebSocket):
        if room_code in self.active_connections:
            self.active_connections[room_code].remove(websocket)
            if not self.active_connections[room_code]:
                del self.active_connections[room_code]
        logger.info(f"WebSocket disconnected from room {room_code}")

    async def broadcast(self, room_code: str, message: Dict[str, Any]):
        if room_code in self.active_connections:
            # Create a list to avoid issues if set size changes during iteration
            sockets = list(self.active_connections[room_code])
            for socket in sockets:
                try:
                    await socket.send_text(json.dumps(message))
                except Exception as e:
                    logger.error(f"Error broadcasting to socket: {e}")

manager = ConnectionManager()

# Background auction tickers
# Maps room_code -> asyncio.Task
active_auction_tickers: Dict[str, asyncio.Task] = {}

# --- HELPER FUNCTIONS ---
def generate_room_code() -> str:
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=6))

async def serialize_team(team: Team, session: AsyncSession) -> Dict[str, Any]:
    # Query players in team
    res = await session.execute(
        select(RoomPlayer)
        .where(RoomPlayer.team_id == team.id)
        .options(selectinload(RoomPlayer.player))
    )
    players = res.scalars().all()
    
    return {
        "id": team.id,
        "room_id": team.room_id,
        "name": team.name,
        "short_name": team.short_name,
        "home_ground": team.home_ground,
        "budget_remaining": team.budget_remaining,
        "rtm_cards_remaining": team.rtm_cards_remaining,
        "is_ai": team.is_ai,
        "wins": team.wins,
        "losses": team.losses,
        "points": team.points,
        "nrr": team.nrr,
        "players": [
            {
                "id": rp.id,
                "player_id": rp.player_id,
                "team_id": rp.team_id,
                "sold_price": rp.sold_price,
                "current_form": rp.current_form,
                "fitness": rp.fitness,
                "status": rp.status,
                "starting_11": rp.starting_11,
                "batting_order": rp.batting_order,
                "bowling_order": rp.bowling_order,
                "player": {
                    "id": rp.player.id,
                    "name": rp.player.name,
                    "role": rp.player.role,
                    "nationality": rp.player.nationality,
                    "batting_avg": rp.player.batting_avg,
                    "strike_rate": rp.player.strike_rate,
                    "bowling_economy": rp.player.bowling_economy,
                    "bowling_avg": rp.player.bowling_avg,
                    "base_price": rp.player.base_price,
                    "pitch_suitability": rp.player.pitch_suitability,
                }
            } for rp in players
        ]
    }

async def serialize_room_state(room_code: str, session: AsyncSession) -> Dict[str, Any]:
    # Fetch room with teams
    res = await session.execute(
        select(Room)
        .where(Room.code == room_code)
        .options(selectinload(Room.teams))
    )
    room = res.scalar_one_or_none()
    if not room:
        return {}

    # Serialize teams
    serialized_teams = []
    for team in room.teams:
        serialized_teams.append(await serialize_team(team, session))

    # Fetch active auction state
    res = await session.execute(
        select(RoomAuctionState)
        .where(RoomAuctionState.room_id == room.id)
    )
    auc_state = res.scalar_one_or_none()
    
    serialized_auc = None
    if auc_state and auc_state.current_player_id:
        # Fetch current player details
        res = await session.execute(
            select(RoomPlayer)
            .where(RoomPlayer.id == auc_state.current_player_id)
            .options(selectinload(RoomPlayer.player))
        )
        rp = res.scalar_one_or_none()
        if rp:
            serialized_auc = {
                "room_id": auc_state.room_id,
                "current_player_id": auc_state.current_player_id,
                "current_bid": auc_state.current_bid,
                "current_bidder_id": auc_state.current_bidder_id,
                "timer_ends_at": f"{auc_state.timer_ends_at.isoformat()}Z" if auc_state.timer_ends_at else None,
                "rtm_active": auc_state.rtm_active,
                "rtm_original_team_id": auc_state.rtm_original_team_id,
                "rtm_timer_ends_at": f"{auc_state.rtm_timer_ends_at.isoformat()}Z" if auc_state.rtm_timer_ends_at else None,
                "current_player": {
                    "id": rp.id,
                    "player_id": rp.player_id,
                    "team_id": rp.team_id,
                    "sold_price": rp.sold_price,
                    "current_form": rp.current_form,
                    "fitness": rp.fitness,
                    "status": rp.status,
                    "player": {
                        "id": rp.player.id,
                        "name": rp.player.name,
                        "role": rp.player.role,
                        "nationality": rp.player.nationality,
                        "batting_avg": rp.player.batting_avg,
                        "strike_rate": rp.player.strike_rate,
                        "bowling_economy": rp.player.bowling_economy,
                        "bowling_avg": rp.player.bowling_avg,
                        "base_price": rp.player.base_price,
                        "pitch_suitability": rp.player.pitch_suitability,
                    }
                }
            }

    return {
        "room_code": room.code,
        "room_status": room.status,
        "teams": serialized_teams,
        "auction_state": serialized_auc
    }

# --- BACKGROUND AUCTION TICKER LOOP ---
async def start_next_player(room_id: str, session: AsyncSession) -> Optional[RoomPlayer]:
    # Select a random UNSOLD player in the room
    res = await session.execute(
        select(RoomPlayer)
        .where(RoomPlayer.room_id == room_id)
        .where(RoomPlayer.status == "UNSOLD")
        .options(selectinload(RoomPlayer.player))
    )
    unsold = res.scalars().all()
    
    res_auc = await session.execute(
        select(RoomAuctionState).where(RoomAuctionState.room_id == room_id)
    )
    auc_state = res_auc.scalar_one_or_none()
    
    if not unsold:
        # No unsold players left!
        if auc_state:
            auc_state.current_player_id = None
            auc_state.current_bid = None
            auc_state.current_bidder_id = None
            auc_state.timer_ends_at = None
            auc_state.rtm_active = False
            auc_state.rtm_original_team_id = None
        return None

    # Pick a random player
    rp = random.choice(unsold)
    rp.status = "AUCTIONING"
    
    if auc_state:
        auc_state.current_player_id = rp.id
        auc_state.current_bid = None # No bid yet, starts at base_price when first bid occurs
        auc_state.current_bidder_id = None
        auc_state.timer_ends_at = datetime.utcnow() + timedelta(seconds=15)
        auc_state.rtm_active = False
        auc_state.rtm_original_team_id = None
        
    await session.commit()
    return rp

async def finalize_sale(room_id: str, winning_team_id: str, price: float, session: AsyncSession, rtm_used: bool = False):
    res_auc = await session.execute(
        select(RoomAuctionState).where(RoomAuctionState.room_id == room_id)
    )
    auc_state = res_auc.scalar_one_or_none()
    if not auc_state or not auc_state.current_player_id:
        return
        
    # Load player and team
    res_rp = await session.execute(
        select(RoomPlayer)
        .where(RoomPlayer.id == auc_state.current_player_id)
        .options(selectinload(RoomPlayer.player))
    )
    rp = res_rp.scalar_one()
    
    res_t = await session.execute(
        select(Team).where(Team.id == winning_team_id)
    )
    team = res_t.scalar_one()
    
    # Update player status
    rp.status = "SOLD"
    rp.team_id = winning_team_id
    rp.sold_price = price
    
    # Update team budget
    team.budget_remaining = round(team.budget_remaining - price, 2)
    if rtm_used:
        # Decrement original team RTM card
        res_orig = await session.execute(
            select(Team).where(Team.id == auc_state.rtm_original_team_id)
        )
        orig_team = res_orig.scalar_one()
        orig_team.rtm_cards_remaining -= 1
        
    await session.commit()

async def finalize_unsold(room_id: str, session: AsyncSession):
    res_auc = await session.execute(
        select(RoomAuctionState).where(RoomAuctionState.room_id == room_id)
    )
    auc_state = res_auc.scalar_one_or_none()
    if not auc_state or not auc_state.current_player_id:
        return
        
    res_rp = await session.execute(
        select(RoomPlayer).where(RoomPlayer.id == auc_state.current_player_id)
    )
    rp = res_rp.scalar_one()
    rp.status = "UNSOLD" # Recycle back into unsold pool
    await session.commit()

async def run_room_auction_ticker(room_code: str):
    logger.info(f"Starting background auction ticker for room {room_code}")
    from backend.database import AsyncSessionLocal
    
    try:
        while True:
            await asyncio.sleep(1) # tick every second
            
            async with AsyncSessionLocal() as session:
                # 1. Fetch Room and Auction state
                res_r = await session.execute(
                    select(Room).where(Room.code == room_code)
                )
                room = res_r.scalar_one_or_none()
                if not room or room.status != "AUCTION":
                    logger.info(f"Stopping ticker for room {room_code}: Room state is {room.status if room else 'None'}")
                    break
                    
                res_auc = await session.execute(
                    select(RoomAuctionState)
                    .where(RoomAuctionState.room_id == room.id)
                )
                auc_state = res_auc.scalar_one_or_none()
                if not auc_state or not auc_state.current_player_id:
                    # If room has no active player, pull next player!
                    next_player = await start_next_player(room.id, session)
                    if next_player:
                        serialized_state = await serialize_room_state(room_code, session)
                        await manager.broadcast(room_code, {
                            "type": "NEW_PLAYER",
                            "message": f"New player up for auction: {next_player.player.name}!",
                            "state": serialized_state
                        })
                    else:
                        # No players left! Finish auction
                        room.status = "MANAGEMENT"
                        # Create fixtures
                        res_teams = await session.execute(
                            select(Team).where(Team.room_id == room.id)
                        )
                        teams = res_teams.scalars().all()
                        teams_dicts = [{"id": t.id, "name": t.name, "short_name": t.short_name, "home_ground": t.home_ground, "is_ai": t.is_ai} for t in teams]
                        
                        fixtures = generate_round_robin_fixtures(teams_dicts)
                        for f in fixtures:
                            match = Match(
                                room_id=room.id,
                                team1_id=f["team1_id"],
                                team2_id=f["team2_id"],
                                venue=f["venue"],
                                stage=f["stage"],
                                status="UPCOMING"
                            )
                            session.add(match)
                        
                        await session.commit()
                        serialized_state = await serialize_room_state(room_code, session)
                        await manager.broadcast(room_code, {
                            "type": "AUCTION_FINISHED",
                            "message": "The auction has successfully completed! Fixtures generated.",
                            "state": serialized_state
                        })
                        break
                    continue
                
                # Check RTM state
                now = datetime.utcnow()
                
                # RTM active and timer ended -> complete sale to high bidder (or original RTM team if matched)
                if auc_state.rtm_active:
                    if auc_state.rtm_timer_ends_at and now >= auc_state.rtm_timer_ends_at:
                        # Human RTM timed out/declined! Sell to high bidder
                        high_bidder_id = auc_state.current_bidder_id
                        final_bid = auc_state.current_bid
                        
                        # Find winning team
                        res_win = await session.execute(select(Team).where(Team.id == high_bidder_id))
                        winning_team = res_win.scalar_one()
                        
                        await finalize_sale(room.id, high_bidder_id, final_bid, session, rtm_used=False)
                        
                        # Set current player to None to trigger next pull on next tick
                        auc_state.current_player_id = None
                        await session.commit()
                        
                        serialized_state = await serialize_room_state(room_code, session)
                        await manager.broadcast(room_code, {
                            "type": "PLAYER_SOLD",
                            "message": f"SOLD! Player went to {winning_team.name} for ₹{final_bid} Cr (RTM declined/timed out).",
                            "state": serialized_state
                        })
                    continue

                # Normal bidding timer ended
                if auc_state.timer_ends_at and now >= auc_state.timer_ends_at:
                    if auc_state.current_bidder_id is None:
                        # Player UNSOLD
                        await finalize_unsold(room.id, session)
                        
                        res_p = await session.execute(
                            select(RoomPlayer).where(RoomPlayer.id == auc_state.current_player_id).options(selectinload(RoomPlayer.player))
                        )
                        rp = res_p.scalar_one()
                        
                        auc_state.current_player_id = None
                        await session.commit()
                        
                        serialized_state = await serialize_room_state(room_code, session)
                        await manager.broadcast(room_code, {
                            "type": "PLAYER_UNSOLD",
                            "message": f"UNSOLD! {rp.player.name} went unsold.",
                            "state": serialized_state
                        })
                    else:
                        # Bidding ended, check for RTM eligibility
                        # Load teams for engine
                        res_teams = await session.execute(
                            select(Team).where(Team.room_id == room.id)
                        )
                        teams = res_teams.scalars().all()
                        
                        # Fetch squad player counts
                        teams_dicts = []
                        for t in teams:
                            t_serialized = await serialize_team(t, session)
                            teams_dicts.append(t_serialized)
                            
                        # Fetch player details
                        res_rp = await session.execute(
                            select(RoomPlayer).where(RoomPlayer.id == auc_state.current_player_id).options(selectinload(RoomPlayer.player))
                        )
                        rp = res_rp.scalar_one()
                        player_dict = {
                            "id": rp.id,
                            "name": rp.player.name,
                            "role": rp.player.role,
                            "nationality": rp.player.nationality,
                            "batting_avg": rp.player.batting_avg,
                            "strike_rate": rp.player.strike_rate,
                            "bowling_economy": rp.player.bowling_economy,
                            "bowling_avg": rp.player.bowling_avg,
                            "base_price": rp.player.base_price,
                            "pitch_suitability": rp.player.pitch_suitability
                        }
                        
                        auc_mgr = AuctionManager({
                            "room_id": room.id,
                            "teams": teams_dicts,
                            "current_auction": {
                                "current_player": player_dict,
                                "current_bid": auc_state.current_bid,
                                "current_bidder_id": auc_state.current_bidder_id,
                                "rtm_active": False
                            }
                        })
                        
                        rtm_eligible, original_team_id = auc_mgr.check_rtm_eligibility()
                        if rtm_eligible:
                            # Trigger RTM phase
                            auc_state.rtm_active = True
                            auc_state.rtm_original_team_id = original_team_id
                            auc_state.rtm_timer_ends_at = datetime.utcnow() + timedelta(seconds=10)
                            await session.commit()
                            
                            # Fetch original team
                            res_orig = await session.execute(select(Team).where(Team.id == original_team_id))
                            orig_team = res_orig.scalar_one()
                            
                            serialized_state = await serialize_room_state(room_code, session)
                            await manager.broadcast(room_code, {
                                "type": "RTM_WINDOW_ACTIVE",
                                "message": f"RTM WINDOW ACTIVE! Can {orig_team.name} match the ₹{auc_state.current_bid} Cr bid for {rp.player.name}?",
                                "rtm_team_id": original_team_id,
                                "state": serialized_state
                            })
                            
                            # If RTM team is AI, evaluate immediately
                            if orig_team.is_ai:
                                # Run AI RTM evaluator
                                rtm_exercised, rtm_msg = auc_mgr.process_ai_rtm()
                                await asyncio.sleep(2.0) # short dramatic delay
                                
                                if rtm_exercised:
                                    # Sell to original team
                                    await finalize_sale(room.id, original_team_id, auc_state.current_bid, session, rtm_used=True)
                                    auc_state.current_player_id = None
                                    await session.commit()
                                    
                                    serialized_state = await serialize_room_state(room_code, session)
                                    await manager.broadcast(room_code, {
                                        "type": "PLAYER_SOLD",
                                        "message": f"SOLD! {orig_team.name} matched the bid using RTM! {rp.player.name} acquired for ₹{auc_state.current_bid} Cr.",
                                        "state": serialized_state
                                    })
                                else:
                                    # Decline RTM, sell to high bidder
                                    res_win = await session.execute(select(Team).where(Team.id == auc_state.current_bidder_id))
                                    winning_team = res_win.scalar_one()
                                    
                                    await finalize_sale(room.id, auc_state.current_bidder_id, auc_state.current_bid, session, rtm_used=False)
                                    auc_state.current_player_id = None
                                    await session.commit()
                                    
                                    serialized_state = await serialize_room_state(room_code, session)
                                    await manager.broadcast(room_code, {
                                        "type": "PLAYER_SOLD",
                                        "message": f"SOLD! {winning_team.name} acquired {rp.player.name} for ₹{auc_state.current_bid} Cr (AI declined RTM).",
                                        "state": serialized_state
                                    })
                        else:
                            # Not eligible for RTM, sell to high bidder
                            res_win = await session.execute(select(Team).where(Team.id == auc_state.current_bidder_id))
                            winning_team = res_win.scalar_one()
                            
                            await finalize_sale(room.id, auc_state.current_bidder_id, auc_state.current_bid, session, rtm_used=False)
                            auc_state.current_player_id = None
                            await session.commit()
                            
                            serialized_state = await serialize_room_state(room_code, session)
                            await manager.broadcast(room_code, {
                                "type": "PLAYER_SOLD",
                                "message": f"SOLD! {winning_team.name} acquired {rp.player.name} for ₹{auc_state.current_bid} Cr.",
                                "state": serialized_state
                            })
                    continue
                
                # Check for AI bids (if timer has not run out and RTM is not active)
                # Load teams and current player to run AuctionManager evaluation
                res_teams = await session.execute(
                    select(Team).where(Team.room_id == room.id)
                )
                teams = res_teams.scalars().all()
                
                # Fetch squad player counts for each team
                teams_dicts = []
                for t in teams:
                    t_serialized = await serialize_team(t, session)
                    teams_dicts.append(t_serialized)
                    
                res_rp = await session.execute(
                    select(RoomPlayer).where(RoomPlayer.id == auc_state.current_player_id).options(selectinload(RoomPlayer.player))
                )
                rp = res_rp.scalar_one()
                player_dict = {
                    "id": rp.id,
                    "name": rp.player.name,
                    "role": rp.player.role,
                    "nationality": rp.player.nationality,
                    "batting_avg": rp.player.batting_avg,
                    "strike_rate": rp.player.strike_rate,
                    "bowling_economy": rp.player.bowling_economy,
                    "bowling_avg": rp.player.bowling_avg,
                    "base_price": rp.player.base_price,
                    "pitch_suitability": rp.player.pitch_suitability
                }
                
                auc_mgr = AuctionManager({
                    "room_id": room.id,
                    "teams": teams_dicts,
                    "current_auction": {
                        "current_player": player_dict,
                        "current_bid": auc_state.current_bid,
                        "current_bidder_id": auc_state.current_bidder_id,
                        "rtm_active": False
                    }
                })
                
                # Run AI bid check (only occasional, say 40% chance per tick to look human-like)
                if random.random() < 0.45:
                    ai_bid = auc_mgr.process_ai_bids()
                    if ai_bid:
                        ai_team_id, bid_amount = ai_bid
                        
                        # Apply bid in database
                        auc_state.current_bid = bid_amount
                        auc_state.current_bidder_id = ai_team_id
                        auc_state.timer_ends_at = datetime.utcnow() + timedelta(seconds=15)
                        await session.commit()
                        
                        res_t = await session.execute(select(Team).where(Team.id == ai_team_id))
                        ai_team = res_t.scalar_one()
                        
                        serialized_state = await serialize_room_state(room_code, session)
                        await manager.broadcast(room_code, {
                            "type": "NEW_BID",
                            "message": f"Bid placed by {ai_team.name}: ₹{bid_amount} Cr",
                            "state": serialized_state
                        })
    except asyncio.CancelledError:
        logger.info(f"Auction ticker for room {room_code} cancelled.")
    except Exception as e:
        logger.error(f"Error in auction ticker loop: {e}", exc_info=True)

# --- REST ENDPOINTS ---

@app.post("/api/rooms", response_model=RoomResponse)
async def create_room(req: RoomCreate, db: AsyncSession = Depends(get_db)):
    code = generate_room_code()
    # Check uniqueness
    while (await db.execute(select(Room).where(Room.code == code))).scalar_one_or_none() is not None:
        code = generate_room_code()
        
    room = Room(code=code, status="LOBBY")
    db.add(room)
    await db.flush() # get room.id
    
    # Initialize the 10 franchises. First team is designated as the creator's team
    creator_team_profile = DEFAULT_TEAMS[0]
    
    creator_team = Team(
        room_id=room.id,
        name=f"{req.username}'s Franchise",
        short_name=f"{req.username[:4].upper()}",
        home_ground=creator_team_profile["home_ground"],
        is_ai=False,
        budget_remaining=90.0
    )
    db.add(creator_team)
    
    # Add other 9 teams as AI opponents
    for i in range(1, 10):
        profile = DEFAULT_TEAMS[i]
        ai_team = Team(
            room_id=room.id,
            name=profile["name"],
            short_name=profile["short_name"],
            home_ground=profile["home_ground"],
            is_ai=True,
            budget_remaining=90.0
        )
        db.add(ai_team)
        
    await db.commit()
    await db.refresh(room)
    
    # Return room with loaded relation
    res = await db.execute(
        select(Room).where(Room.id == room.id).options(selectinload(Room.teams))
    )
    return res.scalar_one()

@app.post("/api/rooms/join")
async def join_room(req: RoomJoin, db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(Room)
        .where(Room.code == req.room_code)
        .options(selectinload(Room.teams))
    )
    room = res.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found.")
        
    if room.status != "LOBBY":
        raise HTTPException(status_code=400, detail="Room is not in lobby state.")
        
    # Check if there's an available AI team that can be assigned to this human player
    ai_teams = [t for t in room.teams if t.is_ai]
    if not ai_teams:
        raise HTTPException(status_code=400, detail="Room is full of human players.")
        
    # Assign the first available AI team to this human player
    team_to_assign = ai_teams[0]
    team_to_assign.is_ai = False
    team_to_assign.name = f"{req.username}'s Franchise"
    team_to_assign.short_name = f"{req.username[:4].upper()}"
    
    await db.commit()
    
    # Broadcast lobby update
    serialized_state = await serialize_room_state(room.code, db)
    await manager.broadcast(room.code, {
        "type": "PLAYER_JOINED",
        "message": f"{req.username} joined the lobby and took over {team_to_assign.name}!",
        "state": serialized_state
    })
    
    return {"room_code": room.code, "assigned_team_id": team_to_assign.id}

@app.post("/api/rooms/{code}/start-auction")
async def start_auction(code: str, exclude_ai: bool = Query(False), db: AsyncSession = Depends(get_db)):
    res = await db.execute(
        select(Room)
        .where(Room.code == code)
        .options(selectinload(Room.teams))
    )
    room = res.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found.")
        
    if room.status != "LOBBY":
        raise HTTPException(status_code=400, detail="Auction already started.")
        
    # Exclude AI teams if requested, maintaining even matchups
    if exclude_ai:
        human_teams = [t for t in room.teams if not t.is_ai]
        ai_teams = [t for t in room.teams if t.is_ai]
        h_count = len(human_teams)
        
        if h_count <= 1:
            keep_ai_count = 1
        elif h_count % 2 == 0:
            keep_ai_count = 0
        else:
            keep_ai_count = 1
            
        teams_to_keep = human_teams + ai_teams[:keep_ai_count]
        teams_to_delete = ai_teams[keep_ai_count:]
        
        for t in teams_to_delete:
            await db.delete(t)
            
        room.teams = teams_to_keep
        await db.flush()
        
    # 1. Seed players from global template table into room_players
    res_players = await db.execute(select(Player))
    global_players = res_players.scalars().all()
    
    if not global_players:
        raise HTTPException(status_code=500, detail="No global players found. Please run seed script first.")
        
    for gp in global_players:
        rp = RoomPlayer(
            room_id=room.id,
            player_id=gp.id,
            sold_price=None,
            current_form=round(random.uniform(0.4, 0.95), 2),
            fitness=1.0,
            status="UNSOLD"
        )
        db.add(rp)
        
    # 2. Initialize RoomAuctionState
    auc_state = RoomAuctionState(room_id=room.id)
    db.add(auc_state)
    
    # 3. Shift status
    room.status = "AUCTION"
    await db.commit()
    
    # Start the background task for this room
    if code in active_auction_tickers:
        active_auction_tickers[code].cancel()
    active_auction_tickers[code] = asyncio.create_task(run_room_auction_ticker(code))
    
    return {"message": "Auction started."}

@app.post("/api/auction/bid")
async def place_bid(req: BidRequest, db: AsyncSession = Depends(get_db)):
    # Fetch team to find room ID
    res_t = await db.execute(select(Team).where(Team.id == req.team_id))
    team = res_t.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found.")
        
    res_r = await db.execute(select(Room).where(Room.id == team.room_id))
    room = res_r.scalar_one()
    
    if room.status != "AUCTION":
        raise HTTPException(status_code=400, detail="Auction is not active.")
        
    # Get active auction state
    res_auc = await db.execute(
        select(RoomAuctionState)
        .where(RoomAuctionState.room_id == room.id)
    )
    auc_state = res_auc.scalar_one()
    
    # Verify RTM active
    if auc_state.rtm_active:
        raise HTTPException(status_code=400, detail="Bidding locked during RTM.")
        
    # Load all teams and their squads for verification
    res_teams = await db.execute(select(Team).where(Team.room_id == room.id))
    teams = res_teams.scalars().all()
    teams_dicts = []
    for t in teams:
        teams_dicts.append(await serialize_team(t, db))
        
    # Fetch player details
    res_rp = await db.execute(
        select(RoomPlayer).where(RoomPlayer.id == auc_state.current_player_id).options(selectinload(RoomPlayer.player))
    )
    rp = res_rp.scalar_one()
    player_dict = {
        "id": rp.id,
        "name": rp.player.name,
        "role": rp.player.role,
        "nationality": rp.player.nationality,
        "batting_avg": rp.player.batting_avg,
        "strike_rate": rp.player.strike_rate,
        "bowling_economy": rp.player.bowling_economy,
        "bowling_avg": rp.player.bowling_avg,
        "base_price": rp.player.base_price,
        "pitch_suitability": rp.player.pitch_suitability
    }
    
    auc_mgr = AuctionManager({
        "room_id": room.id,
        "teams": teams_dicts,
        "current_auction": {
            "current_player": player_dict,
            "current_bid": auc_state.current_bid,
            "current_bidder_id": auc_state.current_bidder_id,
            "rtm_active": False
        }
    })
    
    success, msg = auc_mgr.place_bid(req.team_id, req.amount)
    if not success:
        raise HTTPException(status_code=400, detail=msg)
        
    # Apply changes in DB
    auc_state.current_bid = req.amount
    auc_state.current_bidder_id = req.team_id
    auc_state.timer_ends_at = datetime.utcnow() + timedelta(seconds=15)
    await db.commit()
    
    serialized_state = await serialize_room_state(room.code, db)
    await manager.broadcast(room.code, {
        "type": "NEW_BID",
        "message": f"Bid placed by {team.name}: ₹{req.amount} Cr",
        "state": serialized_state
    })
    
    return {"status": "SUCCESS"}

@app.post("/api/auction/rtm")
async def exercise_rtm(team_id: str, action: str, db: AsyncSession = Depends(get_db)):
    """
    Action can be 'MATCH' or 'DECLINE'
    """
    res_t = await db.execute(select(Team).where(Team.id == team_id))
    team = res_t.scalar_one_or_none()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found.")
        
    res_r = await db.execute(select(Room).where(Room.id == team.room_id))
    room = res_r.scalar_one()
    
    res_auc = await db.execute(
        select(RoomAuctionState)
        .where(RoomAuctionState.room_id == room.id)
    )
    auc_state = res_auc.scalar_one()
    
    if not auc_state.rtm_active or auc_state.rtm_original_team_id != team_id:
        raise HTTPException(status_code=400, detail="RTM is not active for this team.")
        
    res_rp = await db.execute(
        select(RoomPlayer).where(RoomPlayer.id == auc_state.current_player_id).options(selectinload(RoomPlayer.player))
    )
    rp = res_rp.scalar_one()
    
    if action == "MATCH":
        # Sell player to the RTM team
        final_bid = auc_state.current_bid
        await finalize_sale(room.id, team_id, final_bid, db, rtm_used=True)
        auc_state.current_player_id = None
        await db.commit()
        
        serialized_state = await serialize_room_state(room.code, db)
        await manager.broadcast(room.code, {
            "type": "PLAYER_SOLD",
            "message": f"SOLD! {team.name} matched the bid using RTM! {rp.player.name} acquired for ₹{final_bid} Cr.",
            "state": serialized_state
        })
    else:
        # Decline RTM, sell to high bidder
        high_bidder_id = auc_state.current_bidder_id
        final_bid = auc_state.current_bid
        
        res_win = await db.execute(select(Team).where(Team.id == high_bidder_id))
        winning_team = res_win.scalar_one()
        
        await finalize_sale(room.id, high_bidder_id, final_bid, db, rtm_used=False)
        auc_state.current_player_id = None
        await db.commit()
        
        serialized_state = await serialize_room_state(room.code, db)
        await manager.broadcast(room.code, {
            "type": "PLAYER_SOLD",
            "message": f"SOLD! {winning_team.name} acquired {rp.player.name} for ₹{final_bid} Cr (RTM declined).",
            "state": serialized_state
        })
        
    return {"status": "SUCCESS"}

# --- TOURNAMENT ENDPOINTS ---

@app.get("/api/tournament/{room_code}/standings")
async def get_standings(room_code: str, db: AsyncSession = Depends(get_db)):
    res_r = await db.execute(select(Room).where(Room.code == room_code))
    room = res_r.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found.")
        
    res_t = await db.execute(select(Team).where(Team.room_id == room.id))
    teams = res_t.scalars().all()
    teams_dicts = [{"id": t.id, "name": t.name, "short_name": t.short_name, "is_ai": t.is_ai, "wins": t.wins, "losses": t.losses, "points": t.points, "nrr": t.nrr} for t in teams]
    
    # Recalculate standings using completed matches
    res_m = await db.execute(select(Match).where(Match.room_id == room.id))
    matches = res_m.scalars().all()
    matches_dicts = [{
        "status": m.status, "team1_id": m.team1_id, "team2_id": m.team2_id, 
        "scorecard": m.scorecard
    } for m in matches]
    
    standings = recalculate_standings(teams_dicts, matches_dicts)
    return standings

@app.get("/api/tournament/{room_code}/fixtures")
async def get_fixtures(room_code: str, db: AsyncSession = Depends(get_db)):
    res_r = await db.execute(select(Room).where(Room.code == room_code))
    room = res_r.scalar_one_or_none()
    if not room:
        raise HTTPException(status_code=404, detail="Room not found.")
        
    # Query matches with loaded team relations
    res_m = await db.execute(
        select(Match)
        .where(Match.room_id == room.id)
        .options(selectinload(Match.team1), selectinload(Match.team2))
    )
    matches = res_m.scalars().all()
    
    return [
        {
            "id": m.id,
            "room_id": m.room_id,
            "team1_id": m.team1_id,
            "team2_id": m.team2_id,
            "team1_name": m.team1.name,
            "team1_short": m.team1.short_name,
            "team2_name": m.team2.name,
            "team2_short": m.team2.short_name,
            "venue": m.venue,
            "status": m.status,
            "stage": m.stage,
            "result": m.result,
            "innings1_score": m.innings1_score,
            "innings1_wickets": m.innings1_wickets,
            "innings1_overs": m.innings1_overs,
            "innings2_score": m.innings2_score,
            "innings2_wickets": m.innings2_wickets,
            "innings2_overs": m.innings2_overs,
        } for m in matches
    ]

# --- MATCH SIMULATION SETUP & ACTIONS ---

@app.post("/api/match/{match_id}/setup")
async def setup_match_lineup(match_id: str, req: MatchSetupRequest, db: AsyncSession = Depends(get_db)):
    """
    Allows user to choose starting XI, batting order, and bowling order.
    """
    res_m = await db.execute(select(Match).where(Match.id == match_id))
    match = res_m.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found.")
        
    # Reset starting_11 for all players on the human team
    # Find which team the user controls.
    # Check if team1 is human, or team2 is human.
    res_t1 = await db.execute(select(Team).where(Team.id == match.team1_id))
    t1 = res_t1.scalar_one()
    
    res_t2 = await db.execute(select(Team).where(Team.id == match.team2_id))
    t2 = res_t2.scalar_one()
    
    target_team_id = None
    if not t1.is_ai:
        target_team_id = t1.id
    elif not t2.is_ai:
        target_team_id = t2.id
        
    if not target_team_id:
        raise HTTPException(status_code=400, detail="Match does not involve a human player.")
        
    # Clear starting_11 for all players of this team
    await db.execute(
        update(RoomPlayer)
        .where(RoomPlayer.team_id == target_team_id)
        .values(starting_11=False, batting_order=None, bowling_order=None)
    )
    
    # Save the selected starting XI, batting, and bowling orders
    for p_id in req.starting_11:
        bat_idx = req.batting_order.get(p_id)
        bowl_idx = req.bowling_order.get(p_id)
        
        await db.execute(
            update(RoomPlayer)
            .where(RoomPlayer.id == p_id)
            .values(starting_11=True, batting_order=bat_idx, bowling_order=bowl_idx)
        )
        
    await db.commit()
    return {"status": "SUCCESS"}

# Active match simulation caches to stream ball events
# Maps match_id -> MatchSimulator
active_simulators: Dict[str, MatchSimulator] = {}

@app.post("/api/match/{match_id}/simulate-ball")
async def simulate_match_ball(match_id: str, db: AsyncSession = Depends(get_db)):
    res_m = await db.execute(
        select(Match)
        .where(Match.id == match_id)
        .options(selectinload(Match.team1), selectinload(Match.team2))
    )
    match = res_m.scalar_one_or_none()
    if not match:
        raise HTTPException(status_code=404, detail="Match not found.")
        
    if match.status == "COMPLETED":
        return {"status": "COMPLETED", "scorecard": match.scorecard}
        
    # Load players for both teams
    t1_serialized = await serialize_team(match.team1, db)
    t2_serialized = await serialize_team(match.team2, db)
    
    # Verify both teams have starting 11 set up. If not, auto-select them!
    # Especially for AI teams, select starting 11 automatically.
    for t_dict in [t1_serialized, t2_serialized]:
        s11 = [p for p in t_dict["players"] if p["starting_11"]]
        if len(s11) < 11:
            # Auto-assign first 11 players
            logger.info(f"Auto-assigning starting 11 for team {t_dict['name']}")
            # Sort by base stats/role to select best playing XI
            players_sorted = sorted(t_dict["players"], key=lambda x: x["player"]["base_price"], reverse=True)
            for idx, p in enumerate(players_sorted[:11]):
                p["starting_11"] = True
                p["batting_order"] = idx + 1
                
            # Assign bowlers
            bowlers = [p for p in players_sorted[:11] if p["player"]["role"] in ["bowler", "allrounder"]]
            for idx, p in enumerate(bowlers):
                p["bowling_order"] = idx + 1
                
            t_dict["players"] = players_sorted
            
    # Load simulator
    if match_id not in active_simulators:
        match_data = {
            "team1": {
                "id": t1_serialized["id"],
                "name": t1_serialized["name"],
                "short_name": t1_serialized["short_name"],
                "starting_11": [p for p in t1_serialized["players"] if p["starting_11"]]
            },
            "team2": {
                "id": t2_serialized["id"],
                "name": t2_serialized["name"],
                "short_name": t2_serialized["short_name"],
                "starting_11": [p for p in t2_serialized["players"] if p["starting_11"]]
            },
            "venue": match.venue,
            "pitch_type": "NEUTRAL",
            "scorecard": match.scorecard
        }
        active_simulators[match_id] = MatchSimulator(match_data)
        active_simulators[match_id].start_innings()
        
    sim = active_simulators[match_id]
    
    # Simulate single ball
    ball_event = sim.simulate_ball()
    
    # Save scorecard back in DB
    match.scorecard = sim.scorecard
    match.status = sim.scorecard["status"]
    
    # Set display scores
    match.innings1_score = sim.scorecard["innings1"]["total_runs"]
    match.innings1_wickets = sim.scorecard["innings1"]["total_wickets"]
    match.innings1_overs = sim.scorecard["innings1"]["total_overs"]
    match.innings2_score = sim.scorecard["innings2"]["total_runs"]
    match.innings2_wickets = sim.scorecard["innings2"]["total_wickets"]
    match.innings2_overs = sim.scorecard["innings2"]["total_overs"]
    match.result = sim.scorecard["result"]
    
    # If match is completed, clean up standings in database
    if match.status == "COMPLETED":
        # Recalculate standings points, wins, losses for the teams in DB
        res_r = await db.execute(select(Room).where(Room.id == match.room_id))
        room = res_r.scalar_one()
        
        # Load all teams and completed matches to recalculate
        res_teams = await db.execute(select(Team).where(Team.room_id == room.id))
        teams = res_teams.scalars().all()
        teams_dicts = [{"id": t.id, "name": t.name, "short_name": t.short_name, "is_ai": t.is_ai} for t in teams]
        
        res_matches = await db.execute(select(Match).where(Match.room_id == room.id))
        matches = res_matches.scalars().all()
        matches_dicts = [{
            "status": m.status, "team1_id": m.team1_id, "team2_id": m.team2_id, 
            "scorecard": m.scorecard
        } for m in matches]
        
        standings = recalculate_standings(teams_dicts, matches_dicts)
        
        # Save points table stats back to DB teams
        for st in standings:
            await db.execute(
                update(Team)
                .where(Team.id == st["id"])
                .values(wins=st["wins"], losses=st["losses"], points=st["points"], nrr=st["nrr"])
            )
            
        del active_simulators[match_id]
        
    await db.commit()
    
    # Broadcast ball event to WebSocket listeners in the room
    res_r = await db.execute(select(Room).where(Room.id == match.room_id))
    room = res_r.scalar_one()
    
    await manager.broadcast(room.code, {
        "type": "MATCH_BALL_EVENT",
        "match_id": match_id,
        "event": ball_event,
        "scorecard": sim.scorecard
    })
    
    return ball_event

@app.post("/api/match/{match_id}/decision")
async def handle_match_decision(match_id: str, req: MatchDecisionRequest, db: AsyncSession = Depends(get_db)):
    """
    Handles in-match user interactions (bowler changes, DRS reviews).
    """
    if match_id not in active_simulators:
        raise HTTPException(status_code=400, detail="Match simulator is not active.")
        
    sim = active_simulators[match_id]
    
    if req.decision_type == "BOWLER_CHANGE":
        bowler_id = req.details.get("bowler_id")
        if not bowler_id:
            raise HTTPException(status_code=400, detail="Missing bowler_id")
            
        success = sim.change_bowler(bowler_id)
        if not success:
            raise HTTPException(status_code=400, detail="Invalid bowler selection (already bowled 4 overs, or not in squad).")
            
        # Update match scorecard in DB
        res_m = await db.execute(select(Match).where(Match.id == match_id))
        match = res_m.scalar_one()
        match.scorecard = sim.scorecard
        await db.commit()
        
        return {"status": "SUCCESS", "message": "Bowler changed."}
        
    elif req.decision_type == "DRS":
        team_id = req.details.get("team_id")
        if not team_id:
            raise HTTPException(status_code=400, detail="Missing team_id")
            
        drs_res = sim.exercise_drs(team_id)
        if "error" in drs_res:
            raise HTTPException(status_code=400, detail=drs_res["error"])
            
        # Update match scorecard in DB
        res_m = await db.execute(select(Match).where(Match.id == match_id))
        match = res_m.scalar_one()
        match.scorecard = sim.scorecard
        
        # DRS can complete the match if the review stands/overturns last wicket
        match.status = sim.scorecard["status"]
        if match.status == "COMPLETED":
            match.result = sim.scorecard["result"]
            
        await db.commit()
        
        # Broadcast DRS update
        res_r = await db.execute(select(Room).where(Room.id == match.room_id))
        room = res_r.scalar_one()
        await manager.broadcast(room.code, {
            "type": "MATCH_DRS_EVENT",
            "match_id": match_id,
            "drs_result": drs_res,
            "scorecard": sim.scorecard
        })
        
        return drs_res
        
    raise HTTPException(status_code=400, detail="Unknown decision type.")

# --- ROOM WEBSOCKET CONNECTION ---

@app.websocket("/ws/room/{room_code}")
async def room_websocket(websocket: WebSocket, room_code: str, player_id: str = Query(...)):
    """
    WebSocket connection to coordinate room state updates.
    """
    # Open connection
    await manager.connect(room_code, websocket, player_id)
    
    from backend.database import AsyncSessionLocal
    
    # Self-healing: if the room is in AUCTION state, ensure the ticker task is running
    async with AsyncSessionLocal() as session:
        res_r = await session.execute(
            select(Room).where(Room.code == room_code)
        )
        room = res_r.scalar_one_or_none()
        if room and room.status == "AUCTION" and room_code not in active_auction_tickers:
            active_auction_tickers[room_code] = asyncio.create_task(run_room_auction_ticker(room_code))
    
    try:
        # Broadcast initial state immediately
        async with AsyncSessionLocal() as session:
            state = await serialize_room_state(room_code, session)
            await websocket.send_text(json.dumps({
                "type": "INIT_STATE",
                "state": state
            }))
            
        # Listen for client messages
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            logger.info(f"Received websocket message from player {player_id}: {message}")
            
            # Keepalive/ping
            if message.get("type") == "ping":
                await websocket.send_text(json.dumps({"type": "pong"}))
                
    except WebSocketDisconnect:
        manager.disconnect(room_code, websocket)
    except Exception as e:
        logger.error(f"Error in room websocket logic: {e}")
        manager.disconnect(room_code, websocket)

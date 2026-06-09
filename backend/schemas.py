from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime

# --- ROOM SCHEMAS ---
class RoomCreate(BaseModel):
    username: str = Field(..., min_length=2, max_length=20)
    draft_timer_seconds: Optional[int] = Field(30, ge=0)

class RoomJoin(BaseModel):
    room_code: str = Field(..., min_length=6, max_length=6)
    username: str = Field(..., min_length=2, max_length=20)

# --- PLAYER SCHEMAS ---
class PlayerResponse(BaseModel):
    id: int
    name: str
    role: str
    nationality: str
    batting_avg: float
    strike_rate: float
    bowling_economy: float
    bowling_avg: float
    base_price: float
    pitch_suitability: str

    class Config:
        from_attributes = True

class RoomPlayerResponse(BaseModel):
    id: str
    room_id: str
    player_id: int
    team_id: Optional[str] = None
    sold_price: Optional[float] = None
    current_form: float
    fitness: float
    status: str
    starting_11: bool
    batting_order: Optional[int] = None
    bowling_order: Optional[int] = None
    player: PlayerResponse

    class Config:
        from_attributes = True

# --- TEAM SCHEMAS ---
class TeamResponse(BaseModel):
    id: str
    room_id: str
    name: str
    short_name: str
    home_ground: str
    budget_remaining: float
    rtm_cards_remaining: int
    is_ai: bool
    wins: int
    losses: int
    points: int
    nrr: float

    class Config:
        from_attributes = True

class TeamWithPlayersResponse(TeamResponse):
    players: List[RoomPlayerResponse] = []

# --- MATCH SCHEMAS ---
class MatchResponse(BaseModel):
    id: str
    room_id: str
    team1_id: str
    team2_id: str
    venue: str
    status: str
    stage: str
    result: Optional[str] = None
    innings1_score: int
    innings1_wickets: int
    innings1_overs: float
    innings2_score: int
    innings2_wickets: int
    innings2_overs: float
    scorecard: Dict[str, Any] = {}
    
    # We will serialize these manually or use associations
    team1: Optional[TeamResponse] = None
    team2: Optional[TeamResponse] = None

    class Config:
        from_attributes = True

class MatchSetupRequest(BaseModel):
    # Dict mapping player ID (RoomPlayer.id) to batting order (1-11)
    batting_order: Dict[str, int]
    # Dict mapping player ID (RoomPlayer.id) to bowling order (1-5 or similar)
    bowling_order: Dict[str, int]
    # List of player IDs in the starting 11 (must contain exactly 11 player IDs)
    starting_11: List[str]

class MatchDecisionRequest(BaseModel):
    # 'DRS', 'BOWLER_CHANGE', 'IMPACT_PLAYER'
    decision_type: str
    # target bowler room_player_id, or subbed out/in player_ids
    details: Dict[str, Any]

# --- AUCTION STATE ---
class RoomAuctionStateResponse(BaseModel):
    room_id: str
    current_player_id: Optional[str] = None
    current_bid: Optional[float] = None
    current_bidder_id: Optional[str] = None
    timer_ends_at: Optional[datetime] = None
    rtm_active: bool
    rtm_original_team_id: Optional[str] = None
    rtm_timer_ends_at: Optional[datetime] = None
    
    draft_pool_team: Optional[str] = None
    draft_pool_year: Optional[int] = None
    
    current_player: Optional[RoomPlayerResponse] = None

    class Config:
        from_attributes = True

# --- ROOM GENERAL RESPONSE ---
class RoomResponse(BaseModel):
    id: str
    code: str
    status: str
    created_at: datetime
    updated_at: datetime
    teams: List[TeamResponse] = []

    class Config:
        from_attributes = True

# --- BID REQUEST ---
class BidRequest(BaseModel):
    team_id: str
    amount: float

# --- DRAFT REQUEST ---
class DraftRequest(BaseModel):
    team_id: str
    player_id: str

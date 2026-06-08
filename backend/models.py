import uuid
from datetime import datetime
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

try:
    from backend.database import Base
except ModuleNotFoundError:
    from database import Base

class Room(Base):
    __tablename__ = "rooms"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    code = Column(String, unique=True, index=True, nullable=False)
    status = Column(String, default="LOBBY") # LOBBY, AUCTION, MANAGEMENT, TOURNAMENT, FINISHED
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    teams = relationship("Team", back_populates="room", cascade="all, delete-orphan")
    room_players = relationship("RoomPlayer", back_populates="room", cascade="all, delete-orphan")
    matches = relationship("Match", back_populates="room", cascade="all, delete-orphan")
    auction_state = relationship("RoomAuctionState", back_populates="room", uselist=False, cascade="all, delete-orphan")


class Team(Base):
    __tablename__ = "teams"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    room_id = Column(String, ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    short_name = Column(String, nullable=False)
    home_ground = Column(String, nullable=False)
    budget_remaining = Column(Float, default=90.0) # in Crores (₹)
    rtm_cards_remaining = Column(Integer, default=1)
    is_ai = Column(Boolean, default=False)
    wins = Column(Integer, default=0)
    losses = Column(Integer, default=0)
    points = Column(Integer, default=0)
    nrr = Column(Float, default=0.0)

    # Relationships
    room = relationship("Room", back_populates="teams")
    players = relationship("RoomPlayer", back_populates="team")


class Player(Base):
    __tablename__ = "players"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    role = Column(String, nullable=False) # batsman, bowler, allrounder, wicketkeeper
    nationality = Column(String, nullable=False) # Indian, Overseas
    batting_avg = Column(Float, default=0.0)
    strike_rate = Column(Float, default=0.0)
    bowling_economy = Column(Float, default=0.0)
    bowling_avg = Column(Float, default=0.0)
    base_price = Column(Float, nullable=False) # in Crores (₹)
    pitch_suitability = Column(String, default="NEUTRAL") # SPIN, PACE, NEUTRAL
    ipl_team = Column(String, nullable=True) # Original IPL team (e.g., "CSK", "MI")
    ipl_season = Column(Integer, nullable=True) # IPL season year (e.g., 2023, 2024)


class RoomPlayer(Base):
    __tablename__ = "room_players"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    room_id = Column(String, ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False)
    player_id = Column(Integer, ForeignKey("players.id", ondelete="CASCADE"), nullable=False)
    team_id = Column(String, ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)
    
    sold_price = Column(Float, nullable=True) # in Crores (₹)
    current_form = Column(Float, default=0.5) # 0.0 to 1.0
    fitness = Column(Float, default=1.0) # 0.0 to 1.0
    status = Column(String, default="UNSOLD") # UNSOLD, AUCTIONING, SOLD, RECYCLED
    
    # Starting XI / Tactics
    starting_11 = Column(Boolean, default=False)
    batting_order = Column(Integer, nullable=True) # 1 to 11
    bowling_order = Column(Integer, nullable=True)

    # Relationships
    room = relationship("Room", back_populates="room_players")
    player = relationship("Player")
    team = relationship("Team", back_populates="players")


class Match(Base):
    __tablename__ = "matches"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    room_id = Column(String, ForeignKey("rooms.id", ondelete="CASCADE"), nullable=False)
    
    team1_id = Column(String, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    team2_id = Column(String, ForeignKey("teams.id", ondelete="CASCADE"), nullable=False)
    
    venue = Column(String, nullable=False)
    status = Column(String, default="UPCOMING") # UPCOMING, LIVE, COMPLETED
    stage = Column(String, nullable=False) # ROUND_1, QUALIFIER_1, ELIMINATOR, QUALIFIER_2, FINAL
    result = Column(String, nullable=True) # Description of result (e.g. "CSK won by 7 wickets")
    
    innings1_score = Column(Integer, default=0)
    innings1_wickets = Column(Integer, default=0)
    innings1_overs = Column(Float, default=0.0)
    
    innings2_score = Column(Integer, default=0)
    innings2_wickets = Column(Integer, default=0)
    innings2_overs = Column(Float, default=0.0)
    
    # Detailed scorecard including commentary, ball by ball, and player scores
    scorecard = Column(JSON, default=dict)

    # Relationships
    room = relationship("Room", back_populates="matches")
    team1 = relationship("Team", foreign_keys=[team1_id])
    team2 = relationship("Team", foreign_keys=[team2_id])


class RoomAuctionState(Base):
    __tablename__ = "room_auction_states"

    room_id = Column(String, ForeignKey("rooms.id", ondelete="CASCADE"), primary_key=True)
    current_player_id = Column(String, ForeignKey("room_players.id", ondelete="SET NULL"), nullable=True)
    current_bid = Column(Float, nullable=True) # in Crores (₹)
    current_bidder_id = Column(String, ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)
    timer_ends_at = Column(DateTime, nullable=True)
    
    # RTM State
    rtm_active = Column(Boolean, default=False)
    rtm_original_team_id = Column(String, ForeignKey("teams.id", ondelete="SET NULL"), nullable=True)
    rtm_timer_ends_at = Column(DateTime, nullable=True)

    # Relationships
    room = relationship("Room", back_populates="auction_state")
    current_player = relationship("RoomPlayer")
    current_bidder = relationship("Team", foreign_keys=[current_bidder_id])
    rtm_original_team = relationship("Team", foreign_keys=[rtm_original_team_id])

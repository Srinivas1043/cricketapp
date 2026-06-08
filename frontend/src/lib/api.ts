export const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';
export const WS_BASE_URL = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000';

export interface Player {
  id: number;
  name: string;
  role: string;
  nationality: string;
  batting_avg: number;
  strike_rate: number;
  bowling_economy: number;
  bowling_avg: number;
  base_price: number;
  pitch_suitability: string;
}

export interface RoomPlayer {
  id: string;
  room_id: string;
  player_id: number;
  team_id: string | null;
  sold_price: number | null;
  current_form: number;
  fitness: number;
  status: string;
  starting_11: boolean;
  batting_order: number | null;
  bowling_order: number | null;
  player: Player;
}

export interface Team {
  id: string;
  room_id: string;
  name: string;
  short_name: string;
  home_ground: string;
  budget_remaining: number;
  rtm_cards_remaining: number;
  is_ai: boolean;
  wins: number;
  losses: number;
  points: number;
  nrr: number;
  players?: RoomPlayer[];
}

export interface Match {
  id: string;
  room_id: string;
  team1_id: string;
  team2_id: string;
  team1_name: string;
  team1_short: string;
  team2_name: string;
  team2_short: string;
  venue: string;
  status: string;
  stage: string;
  result: string | null;
  innings1_score: number;
  innings1_wickets: number;
  innings1_overs: number;
  innings2_score: number;
  innings2_wickets: number;
  innings2_overs: number;
}

export interface Standing {
  id: string;
  name: string;
  short_name: string;
  wins: number;
  losses: number;
  points: number;
  nrr: number;
  is_ai: boolean;
}

export interface RoomState {
  room_code: string;
  room_status: string; // 'LOBBY', 'AUCTION', 'MANAGEMENT', 'TOURNAMENT', 'FINISHED'
  teams: Team[];
  auction_state: {
    room_id: string;
    current_player_id: string | null;
    current_bid: number | null;
    current_bidder_id: string | null;
    timer_ends_at: string | null;
    rtm_active: boolean;
    rtm_original_team_id: string | null;
    rtm_timer_ends_at: string | null;
    current_player: RoomPlayer | null;
  } | null;
}

export const api = {
  async createRoom(username: string): Promise<RoomResponse> {
    const res = await fetch(`${API_BASE_URL}/api/rooms`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async joinRoom(roomCode: string, username: string): Promise<JoinResponse> {
    const res = await fetch(`${API_BASE_URL}/api/rooms/join`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ room_code: roomCode.toUpperCase(), username }),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async startAuction(roomCode: string): Promise<void> {
    const res = await fetch(`${API_BASE_URL}/api/rooms/${roomCode}/start-auction`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error(await res.text());
  },

  async placeBid(teamId: string, amount: number): Promise<void> {
    const res = await fetch(`${API_BASE_URL}/api/auction/bid`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ team_id: teamId, amount }),
    });
    if (!res.ok) throw new Error(await res.text());
  },

  async exerciseRtm(teamId: string, action: 'MATCH' | 'DECLINE'): Promise<void> {
    const url = new URL(`${API_BASE_URL}/api/auction/rtm`);
    url.searchParams.append('team_id', teamId);
    url.searchParams.append('action', action);
    const res = await fetch(url.toString(), {
      method: 'POST',
    });
    if (!res.ok) throw new Error(await res.text());
  },

  async getStandings(roomCode: string): Promise<Standing[]> {
    const res = await fetch(`${API_BASE_URL}/api/tournament/${roomCode}/standings`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async getFixtures(roomCode: string): Promise<Match[]> {
    const res = await fetch(`${API_BASE_URL}/api/tournament/${roomCode}/fixtures`);
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async setupMatchLineup(matchId: string, payload: {
    starting_11: string[];
    batting_order: Record<string, number>;
    bowling_order: Record<string, number>;
  }): Promise<void> {
    const res = await fetch(`${API_BASE_URL}/api/match/${matchId}/setup`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(await res.text());
  },

  async simulateBall(matchId: string): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/api/match/${matchId}/simulate-ball`, {
      method: 'POST',
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  },

  async matchDecision(matchId: string, payload: {
    decision_type: 'BOWLER_CHANGE' | 'DRS';
    details: Record<string, any>;
  }): Promise<any> {
    const res = await fetch(`${API_BASE_URL}/api/match/${matchId}/decision`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
    });
    if (!res.ok) throw new Error(await res.text());
    return res.json();
  }
};

export interface RoomResponse {
  id: string;
  code: string;
  status: string;
  teams: Team[];
}

export interface JoinResponse {
  room_code: string;
  assigned_team_id: string;
}

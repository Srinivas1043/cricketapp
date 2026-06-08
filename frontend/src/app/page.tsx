'use client';

import React, { useState, useEffect, useRef } from 'react';
import { api, RoomState, Team, RoomPlayer, Match, Standing, WS_BASE_URL } from '../lib/api';
import { 
  Users, DollarSign, Timer, Trophy, Play, Star, 
  ChevronRight, RefreshCw, Radio, CheckCircle, ShieldAlert,
  ArrowRight, UserCheck, BarChart3, Settings, ShieldCheck,
  Award, Eye, AlertTriangle, AlertCircle
} from 'lucide-react';

const getBidIncrement = (currentBid: number): number => {
  if (currentBid < 2.0) {
    return 0.10;  // 10 Lakhs
  } else if (currentBid < 5.0) {
    return 0.20;  // 20 Lakhs
  } else if (currentBid < 10.0) {
    return 0.50;  // 50 Lakhs
  } else {
    return 1.00;  // 1 Crore
  }
};

export default function GamePage() {
  // --- STATE ---
  const [username, setUsername] = useState('');
  const [roomCodeInput, setRoomCodeInput] = useState('');
  const [assignedTeamId, setAssignedTeamId] = useState('');
  const [roomCode, setRoomCode] = useState('');
  const [playerUsername, setPlayerUsername] = useState('');
  const [isHost, setIsHost] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  // Game data state
  const [roomState, setRoomState] = useState<RoomState | null>(null);
  const [activeTab, setActiveTab] = useState<'dashboard' | 'squad' | 'tournament' | 'fixtures'>('dashboard');
  const [fixtures, setFixtures] = useState<Match[]>([]);
  const [standings, setStandings] = useState<Standing[]>([]);
  const [bidLog, setBidLog] = useState<string[]>([]);

  // New modal and filtering states
  const [selectedSquadTeamId, setSelectedSquadTeamId] = useState<string>('');
  const [squadModalTeamId, setSquadModalTeamId] = useState<string | null>(null);
  const [auctionFilter, setAuctionFilter] = useState<'all' | 'friends' | 'ai'>('all');
  const [squadFilter, setSquadFilter] = useState<'all' | 'friends' | 'ai'>('all');
  const [standingsFilter, setStandingsFilter] = useState<'all' | 'friends' | 'ai'>('all');
  const [excludeAi, setExcludeAi] = useState(false);

  // Match center state
  const [activeMatch, setActiveMatch] = useState<Match | null>(null);
  const [matchScorecard, setMatchScorecard] = useState<any>(null);
  const [matchCommentary, setMatchCommentary] = useState<any[]>([]);
  const [matchBalling, setMatchBalling] = useState(false);
  const [selectedBowlerId, setSelectedBowlerId] = useState('');
  const [showBowlerSelect, setShowBowlerSelect] = useState(false);
  const [drsStatus, setDrsStatus] = useState<{status: string, message: string} | null>(null);

  // Refs
  const wsRef = useRef<WebSocket | null>(null);
  const timerIntervalRef = useRef<NodeJS.Timeout | null>(null);
  const [timerDisplay, setTimerDisplay] = useState(15);
  const commEndRef = useRef<HTMLDivElement>(null);

  // Load from localStorage on mount
  useEffect(() => {
    const savedRoom = localStorage.getItem('ipl_room_code');
    const savedTeam = localStorage.getItem('ipl_team_id');
    const savedUsername = localStorage.getItem('ipl_username');
    if (savedRoom && savedTeam && savedUsername) {
      setRoomCode(savedRoom);
      setAssignedTeamId(savedTeam);
      setPlayerUsername(savedUsername);
    }
  }, []);

  // Sync localStorage
  const saveSession = (code: string, teamId: string, name: string) => {
    localStorage.setItem('ipl_room_code', code);
    localStorage.setItem('ipl_team_id', teamId);
    localStorage.setItem('ipl_username', name);
    setRoomCode(code);
    setAssignedTeamId(teamId);
    setPlayerUsername(name);
  };

  const clearSession = () => {
    localStorage.removeItem('ipl_room_code');
    localStorage.removeItem('ipl_team_id');
    localStorage.removeItem('ipl_username');
    setRoomCode('');
    setAssignedTeamId('');
    setPlayerUsername('');
    setRoomState(null);
    if (wsRef.current) wsRef.current.close();
  };

  // --- WEBSOCKET CONNECTION ---
  useEffect(() => {
    if (!roomCode || !assignedTeamId) return;

    const connectWS = () => {
      const url = `${WS_BASE_URL}/ws/room/${roomCode}?player_id=${assignedTeamId}`;
      const ws = new WebSocket(url);
      wsRef.current = ws;

      ws.onopen = () => {
        logger("WebSocket connected.");
        setError('');
      };

      ws.onmessage = (event) => {
        const msg = JSON.parse(event.data);
        handleWSMessage(msg);
      };

      ws.onclose = () => {
        logger("WebSocket disconnected. Reconnecting...");
        setTimeout(() => connectWS(), 3000);
      };

      ws.onerror = (err) => {
        console.error("WebSocket error:", err);
      };
    };

    connectWS();

    return () => {
      if (wsRef.current) wsRef.current.close();
    };
  }, [roomCode, assignedTeamId]);

  const logger = (msg: string) => {
    console.log(`[GameLobby]: ${msg}`);
  };

  const handleWSMessage = (msg: any) => {
    if (msg.state) {
      setRoomState(msg.state);
      
      // Determine if player is host (first team is creator)
      const creatorTeam = msg.state.teams[0];
      if (creatorTeam && creatorTeam.id === assignedTeamId) {
        setIsHost(true);
      }
    }

    switch (msg.type) {
      case 'INIT_STATE':
        logger("Initial state loaded.");
        break;
      case 'PLAYER_JOINED':
      case 'NEW_PLAYER':
      case 'PLAYER_SOLD':
      case 'PLAYER_UNSOLD':
      case 'RTM_WINDOW_ACTIVE':
      case 'NEW_BID':
        if (msg.message) {
          setBidLog((prev) => [msg.message, ...prev.slice(0, 19)]);
        }
        break;
      case 'AUCTION_FINISHED':
        if (msg.message) {
          setBidLog((prev) => [msg.message, ...prev.slice(0, 19)]);
        }
        // Fetch fixtures and standings
        fetchTournamentInfo();
        break;
      case 'MATCH_BALL_EVENT':
        if (activeMatch && msg.match_id === activeMatch.id) {
          setMatchScorecard(msg.scorecard);
          const lastBall = msg.event;
          setMatchCommentary((prev) => [lastBall, ...prev]);
          
          // If over completed, show bowler selection trigger
          if (lastBall.over_completed && !lastBall.match_complete && !lastBall.innings_change) {
            checkBowlerChangeRequirement(msg.scorecard);
          }
        }
        break;
      case 'MATCH_DRS_EVENT':
        if (activeMatch && msg.match_id === activeMatch.id) {
          setMatchScorecard(msg.scorecard);
          setDrsStatus({
            status: msg.drs_result.status,
            message: msg.drs_result.message
          });
          setTimeout(() => setDrsStatus(null), 4000);
          
          // Append DRS commentary
          const lastBall = msg.scorecard.innings1.history[msg.scorecard.innings1.history.length - 1] || 
                           msg.scorecard.innings2.history[msg.scorecard.innings2.history.length - 1];
          if (lastBall) {
            setMatchCommentary((prev) => [
              {
                over_ball: lastBall.over_ball,
                batsman: lastBall.batsman,
                bowler: lastBall.bowler,
                outcome: lastBall.outcome,
                commentary: msg.drs_result.message,
                runs: lastBall.runs
              },
              ...prev
            ]);
          }
        }
        break;
    }
  };

  // Timer Countdown logic
  useEffect(() => {
    if (!roomState?.auction_state) return;
    
    const targetTime = roomState.auction_state.rtm_active 
      ? roomState.auction_state.rtm_timer_ends_at 
      : roomState.auction_state.timer_ends_at;
      
    if (!targetTime) return;

    if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);

    const calcTime = () => {
      const diff = new Date(targetTime).getTime() - new Date().getTime();
      const seconds = Math.max(0, Math.ceil(diff / 1000));
      setTimerDisplay(seconds);
      if (seconds <= 0 && timerIntervalRef.current) {
        clearInterval(timerIntervalRef.current);
      }
    };

    calcTime();
    timerIntervalRef.current = setInterval(calcTime, 1000);

    return () => {
      if (timerIntervalRef.current) clearInterval(timerIntervalRef.current);
    };
  }, [roomState?.auction_state?.timer_ends_at, roomState?.auction_state?.rtm_timer_ends_at, roomState?.auction_state?.rtm_active]);

  // Fetch standings and fixtures once auction is finished
  const fetchTournamentInfo = async () => {
    if (!roomCode) return;
    try {
      const std = await api.getStandings(roomCode);
      setStandings(std);
      const fix = await api.getFixtures(roomCode);
      setFixtures(fix);
    } catch (err: any) {
      console.error(err);
    }
  };

  useEffect(() => {
    if (roomState?.room_status === 'MANAGEMENT' || roomState?.room_status === 'TOURNAMENT') {
      fetchTournamentInfo();
    }
  }, [roomState?.room_status]);

  // --- ACTIONS ---
  const handleCreateRoom = async () => {
    if (!username.trim()) return setError('Please enter a username');
    setLoading(true);
    setError('');
    try {
      const res = await api.createRoom(username);
      // Host team is creator
      const myTeam = res.teams.find(t => !t.is_ai);
      if (myTeam) {
        saveSession(res.code, myTeam.id, username);
      }
    } catch (err: any) {
      setError(err.message || 'Failed to create room');
    } finally {
      setLoading(false);
    }
  };

  const handleJoinRoom = async () => {
    if (!username.trim()) return setError('Please enter a username');
    if (!roomCodeInput.trim()) return setError('Please enter a room code');
    setLoading(true);
    setError('');
    try {
      const res = await api.joinRoom(roomCodeInput, username);
      saveSession(res.room_code, res.assigned_team_id, username);
    } catch (err: any) {
      setError(err.message || 'Room code incorrect or room full');
    } finally {
      setLoading(false);
    }
  };

  const handleStartAuction = async () => {
    if (!roomCode) return;
    try {
      await api.startAuction(roomCode, excludeAi);
    } catch (err: any) {
      setError(err.message);
    }
  };

  const handlePlaceBid = async () => {
    if (!roomState?.auction_state?.current_player) return;
    const team = roomState.teams.find(t => t.id === assignedTeamId);
    if (!team) return;

    const currentBid = roomState.auction_state.current_bid;
    const basePrice = roomState.auction_state.current_player.player.base_price;
    const nextBid = (currentBid === null || currentBid === undefined) 
      ? basePrice 
      : round(currentBid + getBidIncrement(currentBid), 2);

    if (team.budget_remaining < nextBid) {
      alert("You don't have enough budget!");
      return;
    }

    try {
      await api.placeBid(assignedTeamId, nextBid);
    } catch (err: any) {
      alert(err.message);
    }
  };

  const handleRtm = async (action: 'MATCH' | 'DECLINE') => {
    try {
      await api.exerciseRtm(assignedTeamId, action);
    } catch (err: any) {
      alert(err.message);
    }
  };

  // Helper round function
  const round = (num: number, dec: number) => {
    const f = Math.pow(10, dec);
    return Math.round(num * f) / f;
  };

  // --- MATCH SIMULATION ---
  const myTeam = roomState?.teams.find(t => t.id === assignedTeamId);

  const startMatchSim = (match: Match) => {
    setActiveMatch(match);
    setMatchScorecard(null);
    setMatchCommentary([]);
    setMatchBalling(false);
    setShowBowlerSelect(false);
    setSelectedBowlerId('');
  };

  const handleNextBall = async () => {
    if (!activeMatch) return;
    try {
      const res = await api.simulateBall(activeMatch.id);
      if (res.match_complete) {
        setMatchBalling(false);
        fetchTournamentInfo();
      }
    } catch (err: any) {
      console.error(err);
    }
  };

  // Auto Play Over
  useEffect(() => {
    let interval: any;
    if (matchBalling && activeMatch && !showBowlerSelect) {
      interval = setInterval(() => {
        handleNextBall();
      }, 1000); // 1 ball per second
    }
    return () => clearInterval(interval);
  }, [matchBalling, activeMatch, showBowlerSelect]);

  const checkBowlerChangeRequirement = (sc: any) => {
    const isUserBowling = (sc.current_innings_num === 1 && sc.innings1.team_id !== assignedTeamId) || 
                          (sc.current_innings_num === 2 && sc.innings2.team_id !== assignedTeamId);
                          
    if (isUserBowling) {
      setMatchBalling(false);
      setShowBowlerSelect(true);
    } else {
      // AI automatically picks next bowler
      setTimeout(async () => {
        const inn_key = sc.current_innings_num === 1 ? "innings1" : "innings2";
        const bowling_pool = sc[inn_key].bowling;
        // select eligible bowler with least balls bowled
        const eligible = bowling_pool.filter((b: any) => b.balls < 24 && b.id !== sc.current_bowler_id);
        if (eligible.length > 0) {
          const nextB = eligible[Math.floor(Math.random() * eligible.length)];
          try {
            await api.matchDecision(activeMatch!.id, {
              decision_type: 'BOWLER_CHANGE',
              details: { bowler_id: nextB.id }
            });
          } catch (e) {
            console.error("AI bowler change failed", e);
          }
        }
      }, 500);
    }
  };

  const handleSelectBowler = async () => {
    if (!activeMatch || !selectedBowlerId) return;
    try {
      await api.matchDecision(activeMatch.id, {
        decision_type: 'BOWLER_CHANGE',
        details: { bowler_id: selectedBowlerId }
      });
      setShowBowlerSelect(false);
      setSelectedBowlerId('');
    } catch (err: any) {
      alert(err.message || "Cannot change bowler.");
    }
  };

  const handleDRSReview = async () => {
    if (!activeMatch || !matchScorecard) return;
    try {
      await api.matchDecision(activeMatch.id, {
        decision_type: 'DRS',
        details: { team_id: assignedTeamId }
      });
    } catch (err: any) {
      alert(err.message);
    }
  };

  // UI layout helper
  const getRoleIcon = (role: string) => {
    switch(role.toLowerCase()) {
      case 'batsman': return '🏏';
      case 'bowler': return '⚾';
      case 'allrounder': return '⚡';
      case 'wicketkeeper': return '🧤';
      default: return '👤';
    }
  };

  // Squad Overlay Modal
  const renderSquadModal = () => {
    if (!squadModalTeamId || !roomState) return null;
    const team = roomState.teams.find(t => t.id === squadModalTeamId);
    if (!team) return null;

    const players = team.players || [];
    const batsmen = players.filter(p => p.player.role.toLowerCase() === 'batsman');
    const bowlers = players.filter(p => p.player.role.toLowerCase() === 'bowler');
    const allrounders = players.filter(p => p.player.role.toLowerCase() === 'allrounder');
    const keepers = players.filter(p => p.player.role.toLowerCase() === 'wicketkeeper');

    const roleRequirements = [
      { name: 'Batsmen', current: batsmen.length, target: 5, icon: '🏏' },
      { name: 'Keepers', current: keepers.length, target: 2, icon: '🧤' },
      { name: 'Allrounders', current: allrounders.length, target: 3, icon: '⚡' },
      { name: 'Bowlers', current: bowlers.length, target: 5, icon: '⚾' },
    ];

    return (
      <div 
        className="fixed inset-0 bg-black/85 backdrop-blur-md z-50 flex items-center justify-center p-4 transition-all"
        onClick={() => setSquadModalTeamId(null)}
      >
        <div 
          className="bg-zinc-950 border border-zinc-800 rounded-3xl w-full max-w-2xl max-h-[85vh] flex flex-col overflow-hidden shadow-2xl relative animate-in fade-in zoom-in-95 duration-205"
          onClick={(e) => e.stopPropagation()}
        >
          {/* Header */}
          <div className="p-6 border-b border-zinc-900 bg-zinc-900/20 relative">
            <button 
              onClick={() => setSquadModalTeamId(null)}
              className="absolute top-6 right-6 text-zinc-400 hover:text-white p-2 rounded-xl bg-zinc-900 border border-zinc-800 hover:border-zinc-700 transition-all font-mono font-bold text-xs"
            >
              ✕ CLOSE
            </button>
            <div className="space-y-1">
              <span className="text-emerald-400 text-xs font-black uppercase tracking-widest flex items-center gap-1.5">
                <Users className="w-3.5 h-3.5" /> {team.is_ai ? 'AI OPPONENT SQUAD' : 'HUMAN FRANCHISE'}
              </span>
              <h2 className="text-2xl font-black text-white flex items-center gap-2 mt-1">
                {team.name}
                {team.id === assignedTeamId && (
                  <span className="bg-emerald-500 text-zinc-950 text-[10px] font-black px-2 py-0.5 rounded uppercase">YOU</span>
                )}
              </h2>
              <p className="text-xs text-zinc-500">Home Ground: {team.home_ground}</p>
            </div>
            
            {/* Financials / Count grid */}
            <div className="grid grid-cols-3 gap-3 mt-5 pt-4 border-t border-zinc-900">
              <div className="bg-zinc-900/60 border border-zinc-800/80 rounded-xl p-3 text-center">
                <span className="text-[10px] text-zinc-500 uppercase font-black tracking-wider block">Wallet Left</span>
                <span className="text-sm font-extrabold text-emerald-400 mt-0.5 block">₹{team.budget_remaining} Cr</span>
              </div>
              <div className="bg-zinc-900/60 border border-zinc-800/80 rounded-xl p-3 text-center">
                <span className="text-[10px] text-zinc-500 uppercase font-black tracking-wider block">RTM Cards</span>
                <span className="text-base font-extrabold text-amber-400 mt-0.5 block">{team.rtm_cards_remaining}</span>
              </div>
              <div className="bg-zinc-900/60 border border-zinc-800/80 rounded-xl p-3 text-center">
                <span className="text-[10px] text-zinc-500 uppercase font-black tracking-wider block">Draft Count</span>
                <span className="text-base font-extrabold text-zinc-200 mt-0.5 block">{players.length} / 15</span>
              </div>
            </div>
          </div>

          {/* Body */}
          <div className="flex-grow overflow-y-auto p-6 space-y-6 scrollbar-thin scrollbar-thumb-zinc-800 scrollbar-track-transparent">
            {players.length === 0 ? (
              <div className="text-center py-16 text-zinc-500 italic text-sm border border-dashed border-zinc-850 rounded-2xl bg-zinc-900/10">
                No players drafted yet in this franchise.
              </div>
            ) : (
              <div className="space-y-6">
                
                {/* Target checklist progress */}
                <div className="bg-zinc-900/40 border border-zinc-900 rounded-2xl p-4 space-y-3">
                  <span className="text-[10px] text-zinc-500 uppercase font-black tracking-wider block">Squad Balancing Goals</span>
                  <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                    {roleRequirements.map((req) => {
                      const isComplete = req.current >= req.target;
                      return (
                        <div key={req.name} className="p-2 rounded-xl bg-zinc-950/60 border border-zinc-850 flex items-center justify-between text-xs">
                          <div>
                            <span className="text-zinc-500 block text-[9px] font-bold uppercase">{req.icon} {req.name}</span>
                            <span className="font-extrabold text-zinc-200 mt-0.5 block">{req.current} / {req.target}</span>
                          </div>
                          {isComplete ? (
                            <ShieldCheck className="w-4 h-4 text-emerald-400 flex-shrink-0" />
                          ) : (
                            <div className="w-1.5 h-1.5 bg-amber-500/55 rounded-full flex-shrink-0" />
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>

                {/* Categories */}
                {[
                  { title: 'Batsmen', data: batsmen, icon: '🏏' },
                  { title: 'Wicketkeepers', data: keepers, icon: '🧤' },
                  { title: 'Allrounders', data: allrounders, icon: '⚡' },
                  { title: 'Bowlers', data: bowlers, icon: '⚾' }
                ].map(({ title, data, icon }) => {
                  if (data.length === 0) return null;
                  return (
                    <div key={title} className="space-y-2">
                      <h3 className="text-xs uppercase font-extrabold tracking-wider text-zinc-400 flex items-center gap-1.5 border-b border-zinc-900 pb-1.5">
                        <span>{icon}</span> {title} ({data.length})
                      </h3>
                      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                        {data.map((rp) => (
                          <div 
                            key={rp.id}
                            className="bg-zinc-900/30 border border-zinc-900 rounded-xl p-3 flex justify-between items-center text-xs hover:bg-zinc-900/50 transition-all"
                          >
                            <div>
                              <div className="font-extrabold text-zinc-200">{rp.player.name}</div>
                              <span className="text-[10px] text-zinc-500 font-bold block uppercase mt-0.5">
                                {rp.player.nationality}
                              </span>
                            </div>
                            <span className="text-xs bg-zinc-900 px-2 py-1 border border-zinc-850 rounded font-black text-amber-300">
                              ₹{rp.sold_price} Cr
                            </span>
                          </div>
                        ))}
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>
        </div>
      </div>
    );
  };

  // --- RENDER SCREENS ---

  // LOBBY SETUP SCREEN
  if (!roomCode) {
    return (
      <main className="min-h-screen bg-[#0d0f12] text-[#f8fafc] flex flex-col items-center justify-center p-4">
        {/* Glow Header */}
        <div className="absolute top-0 left-0 w-full h-[500px] bg-gradient-to-b from-emerald-500/10 via-amber-500/5 to-transparent pointer-events-none blur-3xl z-0" />
        
        <div className="w-full max-w-lg bg-zinc-900/60 backdrop-blur-xl border border-zinc-800 rounded-3xl p-8 shadow-2xl relative z-10">
          <div className="text-center mb-8">
            <div className="inline-flex items-center justify-center w-16 h-16 rounded-2xl bg-gradient-to-tr from-emerald-500 to-emerald-300 text-zinc-950 font-black text-2xl shadow-lg mb-4">
              DD
            </div>
            <h1 className="text-3xl font-extrabold tracking-tight bg-gradient-to-r from-emerald-400 via-amber-300 to-emerald-400 bg-clip-text text-transparent">
              IPL DUGOUT DYNASTY
            </h1>
            <p className="text-sm text-zinc-400 mt-2">
              Multiplayer franchise management & live match simulation
            </p>
          </div>

          {error && (
            <div className="mb-6 p-4 rounded-xl bg-red-950/40 border border-red-800/60 text-red-300 flex items-center gap-3 text-sm">
              <AlertCircle className="w-5 h-5 flex-shrink-0" />
              <span>{error}</span>
            </div>
          )}

          <div className="space-y-6">
            <div>
              <label className="block text-xs uppercase tracking-wider text-zinc-400 font-bold mb-2">
                Your Manager Name
              </label>
              <input
                type="text"
                placeholder="e.g. Dhoni Fan"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                className="w-full bg-zinc-950/80 border border-zinc-800 focus:border-emerald-500 rounded-xl px-4 py-3 text-sm focus:outline-none transition-all placeholder:text-zinc-600"
              />
            </div>

            <div className="grid grid-cols-1 gap-4 pt-2">
              <button
                onClick={handleCreateRoom}
                disabled={loading}
                className="w-full py-4 bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-400 hover:to-emerald-500 disabled:opacity-50 text-zinc-950 font-bold rounded-xl shadow-lg shadow-emerald-950/20 transition-all flex items-center justify-center gap-2"
              >
                {loading ? <RefreshCw className="w-5 h-5 animate-spin" /> : (
                  <>
                    <span>Create Dynasty Room</span>
                    <ArrowRight className="w-5 h-5" />
                  </>
                )}
              </button>

              <div className="relative flex py-2 items-center">
                <div className="flex-grow border-t border-zinc-800"></div>
                <span className="flex-shrink mx-4 text-zinc-500 text-xs font-bold uppercase tracking-wider">OR JOIN FRIENDS</span>
                <div className="flex-grow border-t border-zinc-800"></div>
              </div>

              <div className="flex gap-2">
                <input
                  type="text"
                  placeholder="ROOM CODE"
                  value={roomCodeInput}
                  onChange={(e) => setRoomCodeInput(e.target.value)}
                  className="bg-zinc-950/80 border border-zinc-800 focus:border-emerald-500 rounded-xl px-4 py-3 text-sm focus:outline-none tracking-widest text-center font-bold placeholder:tracking-normal w-[160px] uppercase transition-all"
                />
                <button
                  onClick={handleJoinRoom}
                  disabled={loading}
                  className="flex-grow py-3 bg-zinc-800 hover:bg-zinc-700 disabled:opacity-50 text-white font-bold rounded-xl border border-zinc-700 transition-all flex items-center justify-center gap-2"
                >
                  Join Room
                </button>
              </div>
            </div>
          </div>
        </div>
      </main>
    );
  }

  // NO ROOM STATE RETRIEVED YET
  if (!roomState) {
    return (
      <main className="min-h-screen bg-[#0d0f12] text-[#f8fafc] flex items-center justify-center p-4">
        <div className="flex flex-col items-center gap-4 text-center">
          <RefreshCw className="w-8 h-8 text-emerald-400 animate-spin" />
          <p className="text-zinc-400 text-sm">Connecting to Dugout Room ({roomCode})...</p>
          <button 
            onClick={clearSession} 
            className="mt-4 px-4 py-2 bg-zinc-900 hover:bg-zinc-800 border border-zinc-800 text-xs font-bold text-red-400 rounded-xl transition-all"
          >
            Cancel & Exit Room
          </button>
        </div>
      </main>
    );
  }

  // LOBBY WAITING SCREEN
  if (roomState.room_status === 'LOBBY') {
    return (
      <main className="min-h-screen bg-[#0d0f12] text-[#f8fafc] p-6 relative">
        <div className="absolute top-0 left-0 w-full h-[300px] bg-gradient-to-b from-emerald-500/5 to-transparent pointer-events-none blur-3xl" />
        
        <div className="max-w-5xl mx-auto space-y-6 relative z-10">
          <div className="flex flex-wrap items-center justify-between gap-4 bg-zinc-900/40 border border-zinc-800 rounded-2xl p-6">
            <div>
              <span className="text-emerald-400 text-xs font-bold uppercase tracking-wider flex items-center gap-1.5 mb-1">
                <Radio className="w-3.5 h-3.5 animate-pulse" /> Lobby Live
              </span>
              <h1 className="text-2xl font-black">IPL DUGOUT DYNASTY</h1>
            </div>
            
            <div className="flex items-center gap-3">
              <span className="text-xs text-zinc-500 font-bold uppercase tracking-wider">Room Code</span>
              <div className="px-4 py-2 bg-zinc-950 border border-zinc-800 rounded-xl text-amber-400 font-mono text-xl font-bold tracking-widest shadow-inner">
                {roomCode}
              </div>
              <button 
                onClick={clearSession} 
                className="text-xs font-bold text-red-400 hover:text-red-300 px-3 py-2 border border-red-950 bg-red-950/20 hover:bg-red-950/40 rounded-xl transition-all"
              >
                Leave
              </button>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            <div className="md:col-span-2 bg-zinc-900/60 border border-zinc-800 rounded-3xl p-6 space-y-4">
              <h2 className="text-lg font-black border-b border-zinc-800 pb-3 flex items-center gap-2">
                <Users className="w-5 h-5 text-emerald-400" /> Room Franchises ({roomState.teams.length} Total)
              </h2>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {roomState.teams.map((t) => (
                  <div 
                    key={t.id}
                    className={`p-4 rounded-xl border flex items-center justify-between ${
                      t.id === assignedTeamId 
                        ? 'bg-emerald-950/20 border-emerald-500/40 shadow-md shadow-emerald-950/10' 
                        : 'bg-zinc-950/50 border-zinc-800'
                    }`}
                  >
                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-extrabold text-sm text-zinc-200">{t.name}</span>
                        {t.id === assignedTeamId && (
                          <span className="text-[10px] bg-emerald-500 text-zinc-950 font-black px-1.5 py-0.5 rounded uppercase">You</span>
                        )}
                      </div>
                      <span className="text-xs font-bold text-zinc-500 flex items-center gap-1.5 mt-0.5">
                        {t.is_ai ? (
                          <span className="bg-zinc-800 text-zinc-400 text-[10px] px-1.5 py-0.5 rounded">AI OPPOSE</span>
                        ) : (
                          <span className="bg-emerald-950/60 border border-emerald-900 text-emerald-400 text-[10px] px-1.5 py-0.5 rounded flex items-center gap-1">
                            <UserCheck className="w-3 h-3" /> HUMAN PLAYER
                          </span>
                        )}
                        • Home: {t.home_ground}
                      </span>
                    </div>
                    
                    <div className="text-right">
                      <span className="text-zinc-500 text-[10px] uppercase font-bold tracking-wider">Budget</span>
                      <div className="text-sm font-extrabold text-zinc-300">₹{t.budget_remaining} Cr</div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            <div className="bg-zinc-900/60 border border-zinc-800 rounded-3xl p-6 space-y-4 flex flex-col justify-between">
              <div className="space-y-4">
                <h2 className="text-lg font-black border-b border-zinc-800 pb-3 flex items-center gap-2">
                  <Settings className="w-5 h-5 text-emerald-400" /> Match Rules
                </h2>
                
                <ul className="text-sm space-y-3 text-zinc-400 font-medium">
                  <li className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-emerald-400" /> ₹90 Crore starting budget</li>
                  <li className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-emerald-400" /> Squad Limit: 15 Players max</li>
                  <li className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-emerald-400" /> 1 Right to Match (RTM) card</li>
                  <li className="flex items-center gap-2"><CheckCircle className="w-4 h-4 text-emerald-400" /> Round Robin (9 matches) + Playoffs</li>
                </ul>
              </div>

              {isHost ? (
                <div className="pt-6 space-y-4">
                  <div className="flex items-center justify-between p-3 rounded-xl bg-zinc-950/40 border border-zinc-800">
                    <div className="flex flex-col">
                      <span className="text-xs font-black text-zinc-300">Exclude AI Teams</span>
                      <span className="text-[10px] text-zinc-500 font-medium">Keep only friend/human franchises</span>
                    </div>
                    <input
                      type="checkbox"
                      id="exclude-ai-checkbox"
                      checked={excludeAi}
                      onChange={(e) => setExcludeAi(e.target.checked)}
                      className="w-4 h-4 rounded border-zinc-700 text-emerald-500 focus:ring-emerald-500 bg-zinc-900 cursor-pointer"
                    />
                  </div>
                  
                  <button
                    onClick={handleStartAuction}
                    className="w-full py-4 bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-400 hover:to-emerald-500 text-zinc-950 font-black rounded-xl shadow-lg shadow-emerald-950/20 transition-all flex items-center justify-center gap-2"
                  >
                    <Play className="w-5 h-5 fill-current" />
                    <span>START AUCTION POOL</span>
                  </button>
                  <p className="text-[10px] text-zinc-500 text-center font-bold uppercase tracking-wider">
                    {excludeAi 
                      ? "Only human teams will play (plus 1 AI if total is odd to maintain even matchups)."
                      : "You are host. Unfilled slots will become AI teams."}
                  </p>
                </div>
              ) : (
                <div className="pt-6 p-4 rounded-xl bg-zinc-950/40 border border-zinc-800 text-center">
                  <span className="text-sm text-zinc-500 font-bold uppercase tracking-wider block">Waiting for Host</span>
                  <span className="text-xs text-zinc-400 mt-1 block">Only the lobby host can start the auction.</span>
                </div>
              )}
            </div>
          </div>
        </div>
      </main>
    );
  }

  // AUCTION ARENA SCREEN
  if (roomState.room_status === 'AUCTION') {
    const curPlayer = roomState.auction_state?.current_player;
    const curBid = roomState.auction_state?.current_bid;
    const curBidderId = roomState.auction_state?.current_bidder_id;
    const rtmActive = roomState.auction_state?.rtm_active;
    const rtmTeamId = roomState.auction_state?.rtm_original_team_id;

    // Find bidder details
    const currentBidder = roomState.teams.find(t => t.id === curBidderId);
    // Find RTM team details
    const rtmTeam = roomState.teams.find(t => t.id === rtmTeamId);

    const isMyRtm = rtmActive && rtmTeamId === assignedTeamId;

    const team = roomState.teams.find(t => t.id === assignedTeamId);
    
    // Bid increment helpers
    const basePrice = curPlayer?.player.base_price || 0;
    const nextBidAmount = (curBid === null || curBid === undefined) 
      ? basePrice 
      : round(curBid + getBidIncrement(curBid), 2);

    return (
      <main className="min-h-screen bg-[#090b0d] text-[#f8fafc] flex flex-col">
        {/* Top bar */}
        <header className="bg-zinc-950 border-b border-zinc-800 py-4 px-6 flex items-center justify-between sticky top-0 z-50">
          <div className="flex items-center gap-4">
            <span className="text-sm font-black tracking-tight bg-gradient-to-r from-emerald-400 to-amber-300 bg-clip-text text-transparent">
              IPL AUCTION ARENA
            </span>
            <div className="text-zinc-600 text-xs">|</div>
            <span className="text-xs font-bold text-zinc-400">Room Code: {roomCode}</span>
            <button 
              onClick={clearSession}
              className="text-[10px] font-bold text-red-400 hover:text-red-300 px-2 py-1 bg-red-950/20 hover:bg-red-950/40 border border-red-950 rounded-lg transition-all"
            >
              Exit Room
            </button>
          </div>

          <div className="flex items-center gap-6">
            <div className="text-right">
              <span className="text-[10px] text-zinc-500 uppercase font-bold tracking-wider block">Your Budget Left</span>
              <span className="text-base font-extrabold text-emerald-400">₹{team?.budget_remaining} Crore</span>
            </div>
            <div className="text-right">
              <span className="text-[10px] text-zinc-500 uppercase font-bold tracking-wider block">RTM Cards Left</span>
              <span className="text-base font-extrabold text-amber-400">{team?.rtm_cards_remaining}</span>
            </div>
            <div className="text-right">
              <span className="text-[10px] text-zinc-500 uppercase font-bold tracking-wider block">Squad Count</span>
              <span className="text-base font-extrabold text-zinc-300">{team?.players?.length}/15</span>
            </div>
          </div>
        </header>

        {/* Main Grid */}
        <div className="flex-grow grid grid-cols-1 lg:grid-cols-4 gap-6 p-6 overflow-hidden">
          
          {/* Column 1: Budgets of all teams */}
          <section className="bg-zinc-900/40 border border-zinc-800 rounded-3xl p-5 space-y-4 overflow-y-auto max-h-[calc(100vh-140px)]">
            <div className="space-y-3 pb-2 border-b border-zinc-800">
              <h2 className="text-xs uppercase font-extrabold tracking-wider text-zinc-400 flex items-center gap-2">
                <DollarSign className="w-4 h-4 text-emerald-500" /> Franchise Budgets
              </h2>
              
              {/* Filter toggle bar */}
              <div className="flex items-center gap-1 bg-zinc-950 p-1 border border-zinc-900 rounded-xl">
                {(['all', 'friends', 'ai'] as const).map((filterOpt) => (
                  <button
                    key={filterOpt}
                    onClick={() => setAuctionFilter(filterOpt)}
                    className={`flex-1 py-1 rounded-lg text-[9px] font-black uppercase text-center transition-all ${
                      auctionFilter === filterOpt
                        ? 'bg-zinc-800 text-emerald-400 shadow-sm'
                        : 'text-zinc-500 hover:text-zinc-350'
                    }`}
                  >
                    {filterOpt === 'friends' ? 'Friends' : filterOpt === 'ai' ? 'AI' : 'All'}
                  </button>
                ))}
              </div>
            </div>

            <div className="space-y-2">
              {roomState.teams
                .filter((t) => {
                  if (auctionFilter === 'friends') return !t.is_ai;
                  if (auctionFilter === 'ai') return t.is_ai;
                  return true;
                })
                .map((t) => (
                  <div 
                    key={t.id}
                    onClick={() => setSquadModalTeamId(t.id)}
                    className={`p-3 rounded-xl border flex items-center justify-between text-xs cursor-pointer transition-all group ${
                      t.id === assignedTeamId 
                        ? 'bg-emerald-950/20 border-emerald-500/30 hover:border-emerald-500/50 hover:bg-emerald-950/30' 
                        : 'bg-zinc-950/60 border-zinc-900 hover:bg-zinc-900/60 hover:border-zinc-800'
                    }`}
                  >
                    <div>
                      <div className="font-extrabold text-zinc-200 flex items-center gap-1.5">
                        <span>{t.name}</span>
                        {t.id === assignedTeamId && (
                          <span className="bg-emerald-500 text-zinc-950 text-[9px] font-black px-1 rounded uppercase">You</span>
                        )}
                      </div>
                      <span className="text-[10px] font-bold text-zinc-500 mt-0.5 flex items-center gap-1.5">
                        Squad: {t.players?.length}/15 • RTM: {t.rtm_cards_remaining}
                        <span className="text-zinc-650 group-hover:text-emerald-400 transition-colors flex items-center gap-0.5 ml-1">
                          <Eye className="w-3 h-3" /> Squad
                        </span>
                      </span>
                    </div>
                    <div className="text-right font-black text-zinc-350 flex-shrink-0">
                      ₹{t.budget_remaining} Cr
                    </div>
                  </div>
                ))}
            </div>
          </section>

          {/* Column 2 & 3: Active Auction Card & Bid control */}
          <section className="lg:col-span-2 flex flex-col justify-between space-y-6">
            {curPlayer ? (
              <div className="flex-grow flex flex-col justify-between">
                
                {/* Player Stats Card */}
                <div className="bg-zinc-900/60 border border-zinc-800 rounded-3xl p-6 relative overflow-hidden flex flex-col md:flex-row gap-6 shadow-2xl">
                  {/* Subtle blur bg glow representing role color */}
                  <div className="absolute top-0 right-0 w-[150px] h-[150px] bg-emerald-500/10 rounded-full blur-3xl pointer-events-none" />
                  
                  {/* Visual Player card representing stats */}
                  <div className="w-full md:w-[180px] h-[220px] bg-gradient-to-b from-zinc-800 to-zinc-950 border-2 border-amber-400/40 rounded-2xl flex flex-col justify-between p-4 shadow-md relative overflow-hidden flex-shrink-0">
                    <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-transparent to-transparent z-0" />
                    
                    <div className="flex justify-between items-center relative z-10">
                      <span className="text-2xl">{getRoleIcon(curPlayer.player.role)}</span>
                      <span className="text-[10px] bg-zinc-800 px-2 py-0.5 rounded font-black text-amber-400 border border-zinc-700 uppercase">
                        {curPlayer.player.nationality}
                      </span>
                    </div>

                    <div className="relative z-10 text-center">
                      <div className="text-[9px] text-zinc-400 font-bold uppercase tracking-wider">IPL TEMPLATE</div>
                      <div className="font-black text-base leading-tight mt-0.5">{curPlayer.player.name}</div>
                      <div className="text-[10px] text-emerald-400 font-extrabold uppercase mt-1">
                        {curPlayer.player.role}
                      </div>
                    </div>

                    <div className="relative z-10 border-t border-zinc-800/80 pt-2 flex items-center justify-between text-xs">
                      <div>
                        <span className="text-[8px] text-zinc-500 uppercase block">Base Price</span>
                        <span className="font-extrabold text-amber-300">₹{curPlayer.player.base_price} Cr</span>
                      </div>
                      <div className="text-right">
                        <span className="text-[8px] text-zinc-500 uppercase block">Pitch Match</span>
                        <span className="font-extrabold text-zinc-300 text-[10px]">{curPlayer.player.pitch_suitability}</span>
                      </div>
                    </div>
                  </div>

                  {/* Player stats info list */}
                  <div className="flex-grow space-y-4">
                    <div>
                      <span className="text-[10px] bg-emerald-500/10 text-emerald-400 border border-emerald-950 font-black px-2.5 py-1 rounded-full uppercase tracking-wider">
                        Current Candidate
                      </span>
                      <h2 className="text-2xl font-black mt-2 text-zinc-100">{curPlayer.player.name}</h2>
                      <p className="text-xs text-zinc-500 mt-0.5">Global Seeding Pool • Realistic Stats</p>
                    </div>

                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 border-t border-zinc-800 pt-4">
                      {curPlayer.player.role.toLowerCase() !== 'bowler' && (
                        <>
                          <div className="bg-zinc-950/40 border border-zinc-900 rounded-xl p-3 text-center">
                            <span className="text-[9px] text-zinc-500 uppercase font-bold block">Batting Avg</span>
                            <span className="text-base font-black text-zinc-200 mt-1 block">{curPlayer.player.batting_avg}</span>
                          </div>
                          <div className="bg-zinc-950/40 border border-zinc-900 rounded-xl p-3 text-center">
                            <span className="text-[9px] text-zinc-500 uppercase font-bold block">Strike Rate</span>
                            <span className="text-base font-black text-zinc-200 mt-1 block">{curPlayer.player.strike_rate}</span>
                          </div>
                        </>
                      )}
                      {curPlayer.player.role.toLowerCase() !== 'batsman' && (
                        <>
                          <div className="bg-zinc-950/40 border border-zinc-900 rounded-xl p-3 text-center">
                            <span className="text-[9px] text-zinc-500 uppercase font-bold block">Economy</span>
                            <span className="text-base font-black text-zinc-200 mt-1 block">{curPlayer.player.bowling_economy}</span>
                          </div>
                          <div className="bg-zinc-950/40 border border-zinc-900 rounded-xl p-3 text-center">
                            <span className="text-[9px] text-zinc-500 uppercase font-bold block">Bowling Avg</span>
                            <span className="text-base font-black text-zinc-200 mt-1 block">{curPlayer.player.bowling_avg}</span>
                          </div>
                        </>
                      )}
                    </div>

                    <div className="p-3 bg-zinc-950/30 border border-zinc-900 rounded-xl text-xs text-zinc-400 space-y-1.5">
                      <div className="flex justify-between">
                        <span>Physical Fitness:</span>
                        <span className="font-extrabold text-zinc-200">{Math.round(curPlayer.fitness * 100)}%</span>
                      </div>
                      <div className="flex justify-between">
                        <span>Current Seeding Form:</span>
                        <span className="font-extrabold text-zinc-200">{curPlayer.current_form} / 1.0</span>
                      </div>
                    </div>
                  </div>
                </div>

                {/* Bidding Control Panel */}
                <div className="bg-zinc-900/60 border border-zinc-800 rounded-3xl p-6 flex flex-col items-stretch gap-6 relative overflow-hidden shadow-2xl">
                  {/* Dynamic Draining Progress Bar */}
                  <div className="absolute top-0 left-0 right-0 h-1.5 bg-zinc-950 overflow-hidden">
                    <div 
                      className={`h-full transition-all duration-1000 ease-linear ${
                        timerDisplay <= 5 
                          ? 'bg-gradient-to-r from-red-600 to-red-500 shadow-[0_0_8px_rgba(239,68,68,0.5)]' 
                          : 'bg-gradient-to-r from-emerald-600 to-emerald-400'
                      }`}
                      style={{ width: `${(timerDisplay / (rtmActive ? 10 : 15)) * 100}%` }}
                    />
                  </div>

                  {/* Sleek Color-coded Status Banner */}
                  <div className={`-mx-6 -mt-6 p-3 text-center text-xs font-black tracking-wide border-b uppercase flex items-center justify-center gap-2 transition-all ${
                    rtmActive
                      ? isMyRtm
                        ? 'bg-amber-950/40 border-amber-900/40 text-amber-300 animate-pulse'
                        : 'bg-zinc-900 border-zinc-800 text-zinc-400'
                      : curBid === null || curBid === undefined
                        ? 'bg-zinc-900 border-zinc-800 text-zinc-400'
                        : curBidderId === assignedTeamId
                          ? 'bg-emerald-950/40 border-emerald-900/40 text-emerald-400 shadow-[inset_0_1px_10px_rgba(16,185,129,0.05)]'
                          : 'bg-red-950/20 border-red-950/40 text-red-400'
                  }`}>
                    {rtmActive ? (
                      isMyRtm ? (
                        <>
                          <span className="w-2 h-2 rounded-full bg-amber-400 animate-ping" />
                          <span>Right To Match Decision Required!</span>
                        </>
                      ) : (
                        <>
                          <span className="w-2 h-2 rounded-full bg-zinc-600" />
                          <span>RTM Window: Waiting for {rtmTeam?.name || 'Owner'}</span>
                        </>
                      )
                    ) : curBid === null || curBid === undefined ? (
                      <>
                        <span className="w-2 h-2 rounded-full bg-amber-400 animate-pulse" />
                        <span>Awaiting first bid from room...</span>
                      </>
                    ) : curBidderId === assignedTeamId ? (
                      <>
                        <span className="w-2 h-2 rounded-full bg-emerald-500 animate-ping" />
                        <span>🎉 You currently hold the highest bid!</span>
                      </>
                    ) : (
                      <>
                        <span className="w-2 h-2 rounded-full bg-red-500 animate-pulse" />
                        <span>⚠️ Outbid! Highest bid held by {currentBidder?.name || 'opponent'}</span>
                      </>
                    )}
                  </div>

                  <div className="flex flex-col md:flex-row items-center justify-between gap-6">
                    {/* Bidding State displays */}
                    <div className="flex-grow space-y-2 text-center md:text-left">
                      <span className="text-[10px] text-zinc-500 uppercase font-bold tracking-wider">Current High Bid</span>
                      <div className="text-4xl font-black text-zinc-100 flex items-center justify-center md:justify-start gap-2">
                        {curBid !== null ? (
                          <>
                            <span>₹{curBid}</span>
                            <span className="text-lg text-zinc-500">Crore</span>
                          </>
                        ) : (
                          <span className="text-xl text-zinc-500 font-bold uppercase tracking-wider">No Bid (Starts at ₹{basePrice} Cr)</span>
                        )}
                      </div>
                      {currentBidder && (
                        <span className="text-xs text-zinc-400 font-bold block">
                          Held by: <span className={curBidderId === assignedTeamId ? "text-emerald-400" : "text-zinc-350"}>{currentBidder.name}</span>
                        </span>
                      )}
                    </div>

                    {/* Live countdown timer */}
                    <div className="flex-shrink-0 flex flex-col items-center justify-center w-28 h-28 border border-zinc-800 rounded-full bg-zinc-950/80 shadow-inner relative">
                      <Timer className={`w-6 h-6 mb-1 ${timerDisplay <= 5 ? 'text-red-500 animate-pulse' : 'text-zinc-500'}`} />
                      <span className={`text-2xl font-black ${timerDisplay <= 5 ? 'text-red-500 animate-pulse' : 'text-zinc-200'}`}>{timerDisplay}s</span>
                      <span className="text-[8px] uppercase tracking-widest text-zinc-650 font-bold mt-0.5">
                        {rtmActive ? 'RTM Lock' : 'Time left'}
                      </span>
                    </div>

                    {/* Manual bid controls */}
                    <div className="w-full md:w-auto flex flex-col gap-2">
                      {rtmActive ? (
                        isMyRtm ? (
                          <div className="p-4 bg-amber-950/20 border border-amber-500/40 rounded-xl space-y-3 text-center">
                            <span className="text-xs text-amber-300 font-bold flex items-center justify-center gap-1.5">
                              <ShieldAlert className="w-4 h-4" /> Exercise RTM Card?
                            </span>
                            <p className="text-[10px] text-zinc-400 max-w-[200px]">
                              Match the bid of ₹{curBid} Cr to retain {curPlayer.player.name}?
                            </p>
                            <div className="flex gap-2">
                              <button
                                onClick={() => handleRtm('MATCH')}
                                className="px-4 py-2 bg-amber-500 hover:bg-amber-400 text-zinc-950 font-black rounded-lg text-xs transition-all shadow-md"
                              >
                                Match Bid (RTM)
                              </button>
                              <button
                                onClick={() => handleRtm('DECLINE')}
                                className="px-3 py-2 bg-zinc-800 hover:bg-zinc-700 text-zinc-300 font-bold rounded-lg text-xs transition-all border border-zinc-700"
                              >
                                Decline
                              </button>
                            </div>
                          </div>
                        ) : (
                          <div className="p-4 bg-zinc-950/50 border border-zinc-800 rounded-xl text-center">
                            <span className="text-[10px] text-zinc-500 uppercase font-bold block tracking-wider">RTM ACTIVE</span>
                            <span className="text-xs font-bold text-amber-400 mt-1 block">
                              Waiting for {rtmTeam?.name} to respond...
                            </span>
                          </div>
                        )
                      ) : (
                        <>
                          <button
                            onClick={handlePlaceBid}
                            disabled={curBidderId === assignedTeamId}
                            className={`px-8 py-4 text-zinc-950 font-black rounded-xl shadow-lg text-sm tracking-wide transition-all uppercase flex items-center justify-center gap-2 ${
                              curBidderId === assignedTeamId 
                                ? 'bg-zinc-800 text-zinc-500 cursor-not-allowed border border-zinc-700 shadow-none' 
                                : 'bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-400 hover:to-emerald-500 hover:shadow-emerald-950/20'
                            }`}
                          >
                            <span>{curBidderId === assignedTeamId ? 'Highest Bidder' : `Bid ₹${nextBidAmount} Cr`}</span>
                            <ChevronRight className="w-4 h-4" />
                          </button>
                          <span className="text-[9px] text-zinc-500 text-center font-bold uppercase tracking-wider block">
                            {curBidderId === assignedTeamId ? 'You currently hold the top spot' : 'Click to submit next bid increment'}
                          </span>
                        </>
                      )}
                    </div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="bg-zinc-900/40 border border-zinc-800 rounded-3xl p-12 text-center flex-grow flex flex-col justify-center items-center gap-4">
                <Trophy className="w-12 h-12 text-emerald-400/30 animate-pulse" />
                <h3 className="font-extrabold text-zinc-400">Auction Loading...</h3>
                <p className="text-xs text-zinc-500 max-w-sm">The auction manager is preparing the first player. Stand by...</p>
              </div>
            )}
          </section>

          {/* Column 4: Bidding Feed log */}
          <section className="bg-zinc-900/40 border border-zinc-800 rounded-3xl p-5 space-y-4 overflow-hidden flex flex-col justify-between max-h-[calc(100vh-140px)]">
            <h2 className="text-xs uppercase font-extrabold tracking-wider text-zinc-400 pb-2 border-b border-zinc-800 flex items-center gap-2">
              <Radio className="w-4 h-4 text-emerald-400 animate-pulse" /> Bidding Feed
            </h2>
            
            <div className="flex-grow overflow-y-auto space-y-3 pr-2 scrollbar-thin scrollbar-thumb-zinc-800 scrollbar-track-transparent">
              {bidLog.length === 0 ? (
                <div className="text-xs text-zinc-600 italic text-center pt-8">
                  No actions logged. Bidding ticker is active...
                </div>
              ) : (
                bidLog.map((log, i) => {
                  let isSold = log.includes("SOLD!");
                  let isNew = log.includes("New player");
                  let isUnsold = log.includes("UNSOLD!");
                  
                  return (
                    <div 
                      key={i} 
                      className={`p-3 rounded-xl border text-xs leading-relaxed font-semibold transition-all ${
                        isSold 
                          ? 'bg-emerald-950/20 border-emerald-950 text-emerald-300' 
                          : isNew
                          ? 'bg-amber-950/15 border-amber-950 text-amber-300'
                          : isUnsold
                          ? 'bg-red-950/15 border-red-950 text-red-400'
                          : 'bg-zinc-950/60 border-zinc-900 text-zinc-400'
                      }`}
                    >
                      {log}
                    </div>
                  );
                })
              )}
              <div ref={commEndRef} />
            </div>
          </section>

        </div>
        {renderSquadModal()}
      </main>
    );
  }

  // --- MANAGEMENT / TOURNAMENT INTERFACE ---

  // MATCH CENTER VIEW
  if (activeMatch) {
    const isCompleted = matchScorecard?.status === "COMPLETED";
    const currentInnings = matchScorecard?.current_innings_num || 1;
    const innKey = currentInnings === 1 ? "innings1" : "innings2";
    const oppInnKey = currentInnings === 1 ? "innings2" : "innings1";
    
    const battingTeamScore = matchScorecard?.[innKey];
    const bowlingTeamScore = matchScorecard?.[oppInnKey];
    
    // Check user roles in active match
    const isUserBatting = battingTeamScore && battingTeamScore.team_id === assignedTeamId;
    const isUserBowling = bowlingTeamScore && bowlingTeamScore.team_id === assignedTeamId;

    // Filter bowlers from current bowling team who haven't bowled 4 overs
    const bowlersList = matchScorecard?.[innKey]?.bowling || [];
    const eligibleBowlers = bowlersList.filter((b: any) => b.balls < 24);

    return (
      <main className="min-h-screen bg-[#07090b] text-[#f8fafc] flex flex-col">
        {/* Header */}
        <header className="bg-zinc-950 border-b border-zinc-800 py-4 px-6 flex items-center justify-between sticky top-0 z-50 shadow-md">
          <div className="flex items-center gap-4">
            <button 
              onClick={() => setActiveMatch(null)}
              className="text-xs font-bold text-zinc-400 hover:text-white px-3 py-1.5 bg-zinc-900 rounded-lg border border-zinc-800 hover:border-zinc-700 transition-all flex items-center gap-1"
            >
              ← Dashboard
            </button>
            <div className="text-zinc-800">|</div>
            <span className="text-xs uppercase font-extrabold tracking-wider text-amber-400">{activeMatch.stage}</span>
            <span className="text-xs text-zinc-500">• Venue: {activeMatch.venue}</span>
          </div>

          <div className="flex items-center gap-4">
            <button 
              onClick={clearSession}
              className="text-[10px] font-bold text-red-400 hover:text-red-350 px-2 py-1 bg-red-950/20 hover:bg-red-950/40 border border-red-950 rounded-lg transition-all"
            >
              Exit Room
            </button>
            <div className="flex items-center gap-2">
              <span className="w-2.5 h-2.5 bg-emerald-500 rounded-full animate-ping" />
              <span className="text-xs font-black text-emerald-400 uppercase tracking-widest">LIVE BROADCAST</span>
            </div>
          </div>
        </header>

        <div className="flex-grow grid grid-cols-1 lg:grid-cols-3 gap-6 p-6">
          
          {/* Left Column: Live Score & Match flow */}
          <div className="lg:col-span-2 space-y-6">
            
            {/* Scoreboard Widget */}
            {matchScorecard ? (
              <div className="bg-gradient-to-r from-zinc-900/80 to-zinc-900/40 border border-zinc-800 rounded-3xl p-6 relative overflow-hidden shadow-2xl flex flex-col justify-between min-h-[200px]">
                {/* Glow representation */}
                <div className="absolute top-0 right-0 w-[120px] h-[120px] bg-emerald-500/5 rounded-full blur-3xl pointer-events-none" />
                
                <div className="flex justify-between items-center border-b border-zinc-800/80 pb-4">
                  <div>
                    <h2 className="text-2xl font-black leading-none flex items-center gap-2">
                      <span className="text-emerald-400">{battingTeamScore?.team_name}</span>
                      <span className="text-sm font-bold text-zinc-500 bg-zinc-950 px-2.5 py-1 border border-zinc-900 rounded-lg uppercase">
                        Batting
                      </span>
                    </h2>
                    <p className="text-xs text-zinc-500 mt-1 font-bold">vs {bowlingTeamScore?.team_name}</p>
                  </div>
                  
                  <div className="text-right">
                    <div className="text-4xl font-black text-white leading-none">
                      {battingTeamScore?.total_runs}/{battingTeamScore?.total_wickets}
                    </div>
                    <div className="text-xs text-zinc-400 font-bold mt-1.5 uppercase tracking-widest">
                      Overs: {battingTeamScore?.total_overs} / 20.0
                    </div>
                  </div>
                </div>

                <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pt-4">
                  {/* Striker/Non-Striker */}
                  <div className="space-y-2">
                    <span className="text-[10px] text-zinc-500 uppercase font-black tracking-wider block">Batsmen at Crease</span>
                    <div className="flex gap-6 text-sm">
                      {battingTeamScore?.batting
                        .filter((b: any) => b.status === "BAT-STRIKER" || b.status === "BAT-NONSTRIKER")
                        .map((b: any) => (
                          <div key={b.id} className="font-extrabold text-zinc-200">
                            <span className={b.status === "BAT-STRIKER" ? "text-emerald-400" : ""}>
                              {b.name}{b.status === "BAT-STRIKER" ? " *" : ""}
                            </span>
                            <span className="text-zinc-500 text-xs font-semibold ml-1.5">
                              {b.runs}({b.balls})
                            </span>
                          </div>
                        ))}
                    </div>
                  </div>

                  {/* Current Bowler */}
                  <div>
                    <span className="text-[10px] text-zinc-500 uppercase font-black tracking-wider block">Active Bowler</span>
                    {matchScorecard.current_bowler_id ? (
                      <div className="font-extrabold text-zinc-200 text-sm mt-1">
                        {battingTeamScore?.bowling.find((b: any) => b.id === matchScorecard.current_bowler_id)?.name || "Default Bowler"}
                        <span className="text-zinc-500 text-xs font-semibold ml-2">
                          {battingTeamScore?.bowling.find((b: any) => b.id === matchScorecard.current_bowler_id)?.overs} - {battingTeamScore?.bowling.find((b: any) => b.id === matchScorecard.current_bowler_id)?.wickets}W - {battingTeamScore?.bowling.find((b: any) => b.id === matchScorecard.current_bowler_id)?.runs}R
                        </span>
                      </div>
                    ) : (
                      <span className="text-xs text-zinc-600 font-bold block mt-1">Selecting Bowler...</span>
                    )}
                  </div>
                </div>

                {/* Chase Target Display */}
                {matchScorecard.target && (
                  <div className="mt-4 p-3 bg-zinc-950/60 border border-zinc-900 rounded-xl flex items-center justify-between text-xs">
                    <span className="text-zinc-400 font-bold">
                      Required: <span className="text-amber-400 font-black">{(matchScorecard.target - battingTeamScore.total_runs)} Runs</span> off <span className="text-zinc-300 font-black">{(120 - battingTeamScore.balls_bowled)} balls</span>
                    </span>
                    <span className="text-zinc-500 font-bold uppercase tracking-wider text-[10px]">
                      Required Rate: {((matchScorecard.target - battingTeamScore.total_runs) / Math.max(1, 120 - battingTeamScore.balls_bowled) * 6.0).toFixed(2)} RPO
                    </span>
                  </div>
                )}
              </div>
            ) : (
              <div className="bg-zinc-900/60 border border-zinc-800 rounded-3xl p-12 text-center flex items-center justify-center min-h-[200px]">
                <div className="flex flex-col items-center gap-2">
                  <Radio className="w-8 h-8 text-emerald-400/40 animate-pulse" />
                  <span className="font-black text-zinc-400">Waiting for first delivery...</span>
                  <button 
                    onClick={handleNextBall}
                    className="mt-4 px-6 py-2.5 bg-emerald-500 text-zinc-950 font-black rounded-xl text-xs uppercase"
                  >
                    Simulate Coin Toss & Start Match
                  </button>
                </div>
              </div>
            )}

            {/* User Interaction decision Panels */}
            {matchScorecard && !isCompleted && (
              <div className="bg-zinc-900/40 border border-zinc-800 rounded-3xl p-6 space-y-4">
                <h3 className="text-xs uppercase font-extrabold tracking-wider text-zinc-400 pb-2 border-b border-zinc-800">
                  Franchise Dugout Control Panel
                </h3>

                <div className="flex flex-wrap gap-4">
                  {/* Next ball controls */}
                  <div className="flex items-center gap-2">
                    <button
                      onClick={handleNextBall}
                      disabled={showBowlerSelect || matchBalling}
                      className="px-5 py-3 bg-gradient-to-r from-emerald-500 to-emerald-600 hover:from-emerald-400 hover:to-emerald-500 text-zinc-950 font-black rounded-xl text-xs uppercase transition-all shadow-md flex items-center gap-1.5"
                    >
                      <Play className="w-4 h-4 fill-current" /> Next Ball
                    </button>
                    
                    <button
                      onClick={() => setMatchBalling(!matchBalling)}
                      disabled={showBowlerSelect}
                      className={`px-4 py-3 font-bold rounded-xl text-xs uppercase border transition-all ${
                        matchBalling 
                          ? 'bg-amber-950/20 border-amber-500/40 text-amber-300' 
                          : 'bg-zinc-800 hover:bg-zinc-700 border-zinc-700 text-zinc-300'
                      }`}
                    >
                      {matchBalling ? 'Pause Simulation' : 'Auto Play Over'}
                    </button>
                  </div>

                  {/* DRS review button */}
                  <div>
                    <button
                      onClick={handleDRSReview}
                      disabled={matchScorecard.drs_available[assignedTeamId] <= 0}
                      className="px-4 py-3 bg-zinc-950 hover:bg-zinc-900 border border-zinc-800 hover:border-zinc-700 text-zinc-300 font-extrabold rounded-xl text-xs uppercase transition-all flex items-center gap-1.5"
                    >
                      Challenge DRS ({matchScorecard.drs_available[assignedTeamId]} left)
                    </button>
                  </div>
                </div>

                {/* Bowler Change overlay/box */}
                {showBowlerSelect && (
                  <div className="p-4 bg-emerald-950/15 border border-emerald-500/30 rounded-xl space-y-3">
                    <span className="text-xs text-emerald-400 font-black flex items-center gap-1.5">
                      <AlertTriangle className="w-4 h-4" /> Selector Required: Choose Next Bowler
                    </span>
                    <p className="text-[10px] text-zinc-400">
                      An over completed. You must select who will bowl the next over from your squad:
                    </p>
                    
                    <div className="flex gap-2">
                      <select
                        value={selectedBowlerId}
                        onChange={(e) => setSelectedBowlerId(e.target.value)}
                        className="bg-zinc-950 border border-zinc-800 focus:border-emerald-500 rounded-lg px-3 py-2 text-xs focus:outline-none focus:ring-0 text-zinc-200"
                      >
                        <option value="">-- Choose Bowler --</option>
                        {eligibleBowlers.map((b: any) => (
                          <option key={b.id} value={b.id}>
                            {b.name} ({(b.balls / 6).toFixed(0)}.{b.balls % 6} overs, {b.wickets}W, {b.runs}R)
                          </option>
                        ))}
                      </select>
                      
                      <button
                        onClick={handleSelectBowler}
                        disabled={!selectedBowlerId}
                        className="px-4 py-2 bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-black rounded-lg text-xs transition-all disabled:opacity-50"
                      >
                        Assign Bowler
                      </button>
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Show completed card details */}
            {isCompleted && (
              <div className="bg-emerald-950/10 border border-emerald-500/30 rounded-3xl p-6 text-center space-y-3">
                <CheckCircle className="w-12 h-12 text-emerald-400 mx-auto" />
                <h3 className="text-xl font-black text-emerald-400">MATCH COMPLETED</h3>
                <p className="text-sm text-zinc-300 font-bold">Result: {matchScorecard.result}</p>
                <button 
                  onClick={() => setActiveMatch(null)}
                  className="px-6 py-2 bg-zinc-800 hover:bg-zinc-700 text-white font-bold rounded-xl text-xs uppercase tracking-wider transition-all"
                >
                  Return to Tournament Hub
                </button>
              </div>
            )}
          </div>

          {/* Right Column: Ball-by-ball commentary log */}
          <div className="bg-zinc-900/40 border border-zinc-800 rounded-3xl p-5 flex flex-col justify-between max-h-[calc(100vh-140px)] shadow-2xl">
            <h3 className="text-xs uppercase font-extrabold tracking-wider text-zinc-400 pb-2 border-b border-zinc-800 flex items-center gap-2">
              <Radio className="w-4 h-4 text-emerald-400 animate-pulse" /> Commentary Box
            </h3>

            {drsStatus && (
              <div className="my-2 p-3 bg-amber-950/20 border border-amber-500/40 rounded-xl text-xs text-amber-300 font-bold animate-bounce text-center">
                📡 DRS DECISION: {drsStatus.message}
              </div>
            )}

            <div className="flex-grow overflow-y-auto space-y-3 pr-2 mt-4 scrollbar-thin scrollbar-thumb-zinc-800 scrollbar-track-transparent">
              {matchCommentary.length === 0 ? (
                <div className="text-xs text-zinc-600 italic text-center pt-8">
                  Coin toss simulation pending. No deliveries yet.
                </div>
              ) : (
                matchCommentary.map((comm, idx) => {
                  const out = comm.outcome;
                  const isWkt = out === "wicket";
                  const isBound = out === "4" || out === "6";
                  
                  return (
                    <div 
                      key={idx} 
                      className={`p-3 rounded-xl border text-xs leading-relaxed font-semibold transition-all ${
                        isWkt 
                          ? 'bg-red-950/25 border-red-950 text-red-300' 
                          : isBound
                          ? 'bg-amber-950/15 border-amber-950 text-amber-300'
                          : 'bg-zinc-950/50 border-zinc-900/80 text-zinc-400'
                      }`}
                    >
                      <div className="flex justify-between items-center mb-1 text-[10px] text-zinc-500 font-bold border-b border-zinc-800/40 pb-1">
                        <span>Ball {comm.over_ball}</span>
                        {isWkt && <span className="bg-red-500 text-zinc-950 px-1.5 py-0.5 rounded font-black text-[9px] uppercase">Wicket</span>}
                        {isBound && <span className="bg-amber-400 text-zinc-950 px-1.5 py-0.5 rounded font-black text-[9px] uppercase">{out} Runs</span>}
                      </div>
                      <div>{comm.commentary}</div>
                      {comm.team_score && (
                        <div className="text-right text-[9px] text-zinc-600 font-bold mt-1">
                          Score: {comm.team_score}
                        </div>
                      )}
                    </div>
                  );
                })
              )}
            </div>
          </div>

        </div>
      </main>
    );
  }

  // GENERAL TOURNAMENT / SQUAD / DASHBOARD PORTAL
  return (
    <main className="min-h-screen bg-[#07090b] text-[#f8fafc] flex flex-col">
      {/* Top Header bar */}
      <header className="bg-zinc-950 border-b border-zinc-800 py-4 px-6 flex items-center justify-between sticky top-0 z-50">
        <div className="flex items-center gap-4">
          <span className="text-base font-black tracking-tight bg-gradient-to-r from-emerald-400 to-amber-300 bg-clip-text text-transparent">
            {myTeam?.name || "IPL DUGOUT DYNASTY"}
          </span>
          <div className="text-zinc-800">|</div>
          <span className="text-xs bg-emerald-950 text-emerald-400 border border-emerald-900 font-black px-2 py-0.5 rounded uppercase">
            Manager: {playerUsername}
          </span>
        </div>

        <div className="flex gap-1 bg-zinc-900 p-1 border border-zinc-800 rounded-xl">
          {(['dashboard', 'squad', 'tournament', 'fixtures'] as const).map((tab) => (
            <button
              key={tab}
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-1.5 rounded-lg text-xs font-bold uppercase transition-all ${
                activeTab === tab 
                  ? 'bg-zinc-800 text-white shadow-sm' 
                  : 'text-zinc-400 hover:text-zinc-200'
              }`}
            >
              {tab}
            </button>
          ))}
        </div>

        <div>
          <button 
            onClick={clearSession} 
            className="text-xs font-bold text-zinc-500 hover:text-red-400 px-3 py-1.5 bg-zinc-900 hover:bg-zinc-900 border border-zinc-800 rounded-xl transition-all"
          >
            Leave Room
          </button>
        </div>
      </header>

      {/* Primary Panels */}
      <div className="max-w-5xl mx-auto w-full p-6 space-y-6">
        
        {/* DASHBOARD TAB */}
        {activeTab === 'dashboard' && (
          <div className="space-y-6">
            {/* Franchise Stats cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-zinc-900/40 border border-zinc-800 rounded-3xl p-6 space-y-2">
                <span className="text-zinc-500 text-[10px] uppercase font-bold tracking-wider">Remaining Wallet</span>
                <div className="text-3xl font-black text-emerald-400">₹{myTeam?.budget_remaining} Cr</div>
                <p className="text-[10px] text-zinc-400 font-medium">Used for future transfer drafts or RTM matching</p>
              </div>

              <div className="bg-zinc-900/40 border border-zinc-800 rounded-3xl p-6 space-y-2">
                <span className="text-zinc-500 text-[10px] uppercase font-bold tracking-wider">IPL Standing Points</span>
                <div className="text-3xl font-black text-amber-400">{myTeam?.points || 0} Points</div>
                <p className="text-[10px] text-zinc-400 font-medium">Wins: {myTeam?.wins} | Losses: {myTeam?.losses}</p>
              </div>

              <div className="bg-zinc-900/40 border border-zinc-800 rounded-3xl p-6 space-y-2">
                <span className="text-zinc-500 text-[10px] uppercase font-bold tracking-wider">Squad Strength</span>
                <div className="text-3xl font-black text-zinc-200">{myTeam?.players?.length} / 15</div>
                <p className="text-[10px] text-zinc-400 font-medium">RTM Cards left: {myTeam?.rtm_cards_remaining}</p>
              </div>
            </div>

            {/* MORALE & NEXT GAME */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <div className="bg-zinc-900/40 border border-zinc-800 rounded-3xl p-6 space-y-4">
                <h3 className="text-sm font-black border-b border-zinc-800 pb-2 flex items-center gap-2">
                  <BarChart3 className="w-5 h-5 text-emerald-400" /> Morale Indicator
                </h3>
                <div className="flex items-center gap-4">
                  <div className="relative flex items-center justify-center w-20 h-20 border border-zinc-800 rounded-full bg-zinc-950/80">
                    <span className="text-xl font-black text-emerald-400">92%</span>
                  </div>
                  <div className="space-y-1">
                    <span className="text-xs font-bold text-zinc-200 block">Dugout Morale is High!</span>
                    <p className="text-[10px] text-zinc-400 max-w-[300px]">
                      Excellent auction selection and player roster depth. Squad physical fitness is stable.
                    </p>
                  </div>
                </div>
              </div>

              <div className="bg-zinc-900/40 border border-zinc-800 rounded-3xl p-6 space-y-4 flex flex-col justify-between">
                <h3 className="text-sm font-black border-b border-zinc-800 pb-2 flex items-center gap-2">
                  <Award className="w-5 h-5 text-emerald-400" /> Upcoming Match Fixture
                </h3>

                {fixtures.find(m => m.status === 'UPCOMING' && (m.team1_id === assignedTeamId || m.team2_id === assignedTeamId)) ? (
                  (() => {
                    const match = fixtures.find(m => m.status === 'UPCOMING' && (m.team1_id === assignedTeamId || m.team2_id === assignedTeamId))!;
                    const oppName = match.team1_id === assignedTeamId ? match.team2_name : match.team1_name;
                    return (
                      <div className="space-y-4">
                        <div className="flex items-center justify-between text-xs font-bold">
                          <span className="bg-zinc-950 px-2.5 py-1 border border-zinc-900 rounded-lg text-amber-400 uppercase">
                            {match.stage}
                          </span>
                          <span className="text-zinc-500">Venue: {match.venue}</span>
                        </div>
                        <div className="flex items-center justify-between">
                          <span className="font-extrabold text-sm">{myTeam?.name}</span>
                          <span className="text-xs text-zinc-500 font-black uppercase">VS</span>
                          <span className="font-extrabold text-sm">{oppName}</span>
                        </div>
                        <button
                          onClick={() => startMatchSim(match)}
                          className="w-full py-2 bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-black rounded-xl text-xs uppercase transition-all shadow-md"
                        >
                          Play Match simulation
                        </button>
                      </div>
                    );
                  })()
                ) : (
                  <div className="text-xs text-zinc-500 italic text-center py-6">
                    No upcoming fixtures left. Tournament has finished!
                  </div>
                )}
              </div>
            </div>
          </div>
        )}

        {/* SQUAD TAB */}
        {activeTab === 'squad' && (() => {
          const activeSquadTeamId = selectedSquadTeamId || assignedTeamId;
          const activeSquadTeam = roomState?.teams.find(t => t.id === activeSquadTeamId) || myTeam;
          
          return (
            <div className="bg-zinc-900/40 border border-zinc-800 rounded-3xl p-6 space-y-6">
              <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 border-b border-zinc-800 pb-4">
                <div className="space-y-1">
                  <h2 className="text-lg font-black flex items-center gap-2">
                    <Users className="w-5 h-5 text-emerald-400" /> Squad Management
                  </h2>
                  <p className="text-[10px] text-zinc-500 uppercase font-black">
                    {activeSquadTeam?.name} • Wallet Left: ₹{activeSquadTeam?.budget_remaining} Cr • RTMs: {activeSquadTeam?.rtm_cards_remaining}
                  </p>
                </div>
                
                {/* Filter toggle bar */}
                <div className="flex items-center gap-1.5 bg-zinc-950 p-1 border border-zinc-900 rounded-xl flex-shrink-0">
                  {(['all', 'friends', 'ai'] as const).map((filterOpt) => (
                    <button
                      key={filterOpt}
                      onClick={() => setSquadFilter(filterOpt)}
                      className={`px-3 py-1 rounded-lg text-[10px] font-black uppercase transition-all ${
                        squadFilter === filterOpt
                          ? 'bg-zinc-800 text-emerald-400 shadow-sm'
                          : 'text-zinc-500 hover:text-zinc-350'
                      }`}
                    >
                      {filterOpt === 'friends' ? 'Friends' : filterOpt === 'ai' ? 'AI Teams' : 'All'}
                    </button>
                  ))}
                </div>
              </div>

              {/* Franchise Selector Buttons */}
              {roomState && (
                <div className="flex flex-wrap gap-2 pb-4 border-b border-zinc-900/40">
                  {roomState.teams
                    .filter((t) => {
                      if (squadFilter === 'friends') return !t.is_ai;
                      if (squadFilter === 'ai') return t.is_ai;
                      return true;
                    })
                    .map((t) => {
                      const isActive = t.id === activeSquadTeamId;
                      return (
                        <button
                          key={t.id}
                          onClick={() => setSelectedSquadTeamId(t.id)}
                          className={`px-3 py-1.5 rounded-xl text-xs font-bold uppercase transition-all flex items-center gap-1.5 ${
                            isActive
                              ? 'bg-emerald-500 text-zinc-950 font-black shadow-md shadow-emerald-500/10'
                              : 'bg-zinc-950/60 border border-zinc-850 text-zinc-400 hover:text-zinc-200 hover:bg-zinc-900'
                          }`}
                        >
                          <span>{t.short_name}</span>
                          {t.id === assignedTeamId && (
                            <span className={`text-[8px] px-1 rounded font-black ${
                              isActive ? 'bg-zinc-950 text-emerald-400' : 'bg-emerald-500 text-zinc-950'
                            }`}>
                              YOU
                            </span>
                          )}
                        </button>
                      );
                    })}
                </div>
              )}

              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
                {activeSquadTeam?.players?.map((rp) => (
                  <div key={rp.id} className="bg-zinc-950/60 border border-zinc-900 rounded-2xl p-4 flex flex-col justify-between gap-3 shadow-md relative overflow-hidden">
                    <div className="absolute top-0 right-0 w-[80px] h-[80px] bg-emerald-500/5 rounded-full blur-2xl pointer-events-none" />
                    
                    <div className="flex justify-between items-start">
                      <div>
                        <span className="text-xs font-black text-zinc-200">{rp.player.name}</span>
                        <span className="text-[10px] text-zinc-500 block uppercase font-bold mt-0.5">
                          {getRoleIcon(rp.player.role)} {rp.player.role} • {rp.player.nationality}
                        </span>
                      </div>
                      <span className="text-[10px] bg-zinc-900 px-2 py-0.5 border border-zinc-800 rounded font-black text-amber-300 flex-shrink-0">
                        ₹{rp.sold_price} Cr
                      </span>
                    </div>

                    <div className="border-t border-zinc-900/80 pt-2 grid grid-cols-2 gap-2 text-[10px] font-bold text-zinc-400">
                      <div>Form: <span className="text-zinc-200">{rp.current_form}</span></div>
                      <div>Fitness: <span className="text-zinc-200">{Math.round(rp.fitness * 100)}%</span></div>
                      {rp.player.role.toLowerCase() !== 'bowler' && <div>Bat Avg: <span className="text-zinc-200">{rp.player.batting_avg}</span></div>}
                      {rp.player.role.toLowerCase() !== 'batsman' && <div>Bowl Econ: <span className="text-zinc-200">{rp.player.bowling_economy}</span></div>}
                    </div>
                  </div>
                ))}

                {(!activeSquadTeam?.players || activeSquadTeam.players.length === 0) && (
                  <div className="col-span-full py-12 text-center text-xs text-zinc-500 italic">
                    No players drafted yet in {activeSquadTeam?.name || 'this team'}.
                  </div>
                )}
              </div>
            </div>
          );
        })()}

        {/* TOURNAMENT STANDINGS TAB */}
        {activeTab === 'tournament' && (
          <div className="bg-zinc-900/40 border border-zinc-800 rounded-3xl p-6 space-y-4">
            <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-4 pb-3 border-b border-zinc-800">
              <h2 className="text-lg font-black flex items-center gap-2">
                <Trophy className="w-5 h-5 text-emerald-400" /> Tournament League Standings
              </h2>
              
              {/* Filter toggle bar */}
              <div className="flex items-center gap-1.5 bg-zinc-950 p-1 border border-zinc-900 rounded-xl flex-shrink-0">
                {(['all', 'friends', 'ai'] as const).map((filterOpt) => (
                  <button
                    key={filterOpt}
                    onClick={() => setStandingsFilter(filterOpt)}
                    className={`px-3 py-1 rounded-lg text-[10px] font-black uppercase transition-all ${
                      standingsFilter === filterOpt
                        ? 'bg-zinc-800 text-emerald-400 shadow-sm'
                        : 'text-zinc-500 hover:text-zinc-350'
                    }`}
                  >
                    {filterOpt === 'friends' ? 'Friends' : filterOpt === 'ai' ? 'AI Teams' : 'All'}
                  </button>
                ))}
              </div>
            </div>
            
            <div className="overflow-x-auto">
              <table className="w-full text-xs text-left border-collapse">
                <thead>
                  <tr className="border-b border-zinc-800 text-[10px] text-zinc-500 uppercase font-black">
                    <th className="py-3 px-2">Pos</th>
                    <th className="py-3 px-2">Franchise</th>
                    <th className="py-3 px-2 text-center">Played</th>
                    <th className="py-3 px-2 text-center">Won</th>
                    <th className="py-3 px-2 text-center">Lost</th>
                    <th className="py-3 px-2 text-center font-bold text-zinc-300">Points</th>
                    <th className="py-3 px-2 text-right">NRR</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-zinc-900">
                  {standings
                    .filter((st) => {
                      if (standingsFilter === 'friends') return !st.is_ai;
                      if (standingsFilter === 'ai') return st.is_ai;
                      return true;
                    })
                    .map((st, idx) => (
                      <tr 
                        key={st.id} 
                        className={`hover:bg-zinc-950/40 transition-all ${
                          st.id === assignedTeamId ? 'bg-emerald-950/10' : ''
                        }`}
                      >
                        <td className="py-3 px-2 font-bold text-zinc-400">{idx + 1}</td>
                        <td 
                          className="py-3 px-2 font-extrabold text-zinc-200 flex items-center gap-2 cursor-pointer hover:text-emerald-400 transition-colors group"
                          onClick={() => setSquadModalTeamId(st.id)}
                        >
                          <span>{st.name}</span>
                          {st.id === assignedTeamId && (
                            <span className="bg-emerald-500 text-zinc-950 text-[8px] font-black px-1 rounded uppercase">You</span>
                          )}
                          <span className="text-zinc-750 group-hover:text-emerald-400 opacity-0 group-hover:opacity-100 transition-all ml-1 text-[9px] flex items-center gap-0.5">
                            <Eye className="w-3 h-3" /> Squad
                          </span>
                        </td>
                        <td className="py-3 px-2 text-center font-semibold">{st.wins + st.losses}</td>
                        <td className="py-3 px-2 text-center font-semibold text-emerald-500">{st.wins}</td>
                        <td className="py-3 px-2 text-center font-semibold text-red-500">{st.losses}</td>
                        <td className="py-3 px-2 text-center font-black text-amber-400">{st.points}</td>
                        <td className={`py-3 px-2 text-right font-mono font-bold ${st.nrr >= 0 ? 'text-emerald-500' : 'text-red-500'}`}>
                          {st.nrr >= 0 ? `+${st.nrr.toFixed(3)}` : st.nrr.toFixed(3)}
                        </td>
                      </tr>
                    ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {/* FIXTURES TAB */}
        {activeTab === 'fixtures' && (
          <div className="bg-zinc-900/40 border border-zinc-800 rounded-3xl p-6 space-y-6">
            <div className="flex justify-between items-center border-b border-zinc-800 pb-3">
              <h2 className="text-lg font-black flex items-center gap-2">
                <Play className="w-5 h-5 text-emerald-400 fill-current" /> Tournament Match Fixtures
              </h2>
            </div>

            <div className="space-y-6">
              {/* Group fixtures by round */}
              {(() => {
                const rounds: Record<string, Match[]> = {};
                fixtures.forEach(m => {
                  if (!rounds[m.stage]) rounds[m.stage] = [];
                  rounds[m.stage].push(m);
                });
                
                return Object.entries(rounds).map(([roundName, roundMatches]) => (
                  <div key={roundName} className="space-y-3">
                    <h3 className="text-xs uppercase font-extrabold tracking-widest text-amber-400 border-b border-zinc-900 pb-1.5">
                      {roundName.replace("_", " ")}
                    </h3>
                    
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                      {roundMatches.map((match) => {
                        const isInvolvingUser = match.team1_id === assignedTeamId || match.team2_id === assignedTeamId;
                        const isSimulated = match.status === "COMPLETED";
                        
                        return (
                          <div 
                            key={match.id} 
                            className={`p-4 rounded-2xl border flex flex-col justify-between gap-3 transition-all ${
                              isSimulated 
                                ? 'bg-zinc-950/20 border-zinc-950 text-zinc-500' 
                                : isInvolvingUser
                                ? 'bg-emerald-950/10 border-emerald-500/20'
                                : 'bg-zinc-950/50 border-zinc-900'
                            }`}
                          >
                            <div className="flex justify-between items-center text-[10px] font-bold">
                              <span>Venue: {match.venue}</span>
                              {isSimulated ? (
                                <span className="bg-zinc-900 text-zinc-500 px-2 py-0.5 rounded font-black border border-zinc-850">
                                  SIMULATED
                                </span>
                              ) : (
                                <span className="bg-emerald-950 text-emerald-400 px-2 py-0.5 rounded font-black border border-emerald-900 animate-pulse">
                                  UPCOMING
                                </span>
                              )}
                            </div>

                            <div className="flex justify-between items-center text-sm font-semibold">
                              <span className={match.team1_id === assignedTeamId ? 'text-zinc-200' : ''}>
                                {match.team1_name}
                              </span>
                              <span className="text-xs text-zinc-600 uppercase font-black px-2">vs</span>
                              <span className={match.team2_id === assignedTeamId ? 'text-zinc-200' : ''}>
                                {match.team2_name}
                              </span>
                            </div>

                            {/* Scores display if completed */}
                            {isSimulated && (
                              <div className="flex justify-between items-center text-xs border-t border-zinc-900 pt-2 font-mono font-bold text-zinc-400">
                                <span>{match.innings1_score}/{match.innings1_wickets} ({match.innings1_overs})</span>
                                <span>{match.innings2_score}/{match.innings2_wickets} ({match.innings2_overs})</span>
                              </div>
                            )}

                            {/* Result or Action */}
                            {isSimulated ? (
                              <div className="text-[10px] text-zinc-400 font-bold border-t border-zinc-900 pt-2">
                                Result: {match.result}
                              </div>
                            ) : (
                              isInvolvingUser && (
                                <button
                                  onClick={() => startMatchSim(match)}
                                  className="w-full mt-1 py-2 bg-emerald-500 hover:bg-emerald-400 text-zinc-950 font-black rounded-xl text-xs uppercase tracking-wider transition-all"
                                >
                                  PLAY MATCH SIMULATION
                                </button>
                              )
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>
                ));
              })()}
            </div>
          </div>
        )}

      </div>
      {renderSquadModal()}
    </main>
  );
}

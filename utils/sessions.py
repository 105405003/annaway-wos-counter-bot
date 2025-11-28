"""
Session Management
Manages timer states and counting sessions for each Guild
"""
from typing import Dict, Optional, List
import discord
from datetime import datetime
import asyncio
import logging

logger = logging.getLogger(__name__)

class TimerSession:
    """Single Timer Session"""
    
    def __init__(self, timer_id: str, name: str, t_end: datetime, 
                 total_seconds: int):
        self.timer_id = timer_id
        self.name = name
        self.t_end = t_end
        self.total_seconds = total_seconds
        self.discord_message: Optional[discord.Message] = None
        self.status = "active"  # active, completed, deleted
        
    def get_remaining_seconds(self) -> int:
        """Get remaining seconds"""
        remaining = (self.t_end - datetime.now()).total_seconds()
        return max(0, int(remaining))

class SessionManager:
    """Session Manager"""
    
    def __init__(self):
        self._sessions: Dict[str, Dict[str, TimerSession]] = {}
        
    def create_session(self, guild_id: int, timer_id: str, name: str,
                      t_end: datetime, total_seconds: int) -> TimerSession:
        """Create new session"""
        if guild_id not in self._sessions:
            self._sessions[guild_id] = {}
            
        session = TimerSession(timer_id, name, t_end, total_seconds)
        self._sessions[guild_id][timer_id] = session
        return session
        
    def get_session(self, guild_id: int, timer_id: str) -> Optional[TimerSession]:
        """Get session"""
        if guild_id not in self._sessions:
            return None
        return self._sessions[guild_id].get(timer_id)
        
    def get_guild_sessions(self, guild_id: int) -> Dict[str, TimerSession]:
        """Get all sessions for a Guild"""
        return self._sessions.get(guild_id, {})
        
    def remove_session(self, guild_id: int, timer_id: str):
        """Remove session"""
        if guild_id in self._sessions and timer_id in self._sessions[guild_id]:
            del self._sessions[guild_id][timer_id]
            
    def get_all_timers(self) -> int:
        """Get total timer count"""
        total = 0
        for guild_sessions in self._sessions.values():
            total += len(guild_sessions)
        return total


# ============================================
# Counter Bot Session Management
# ============================================

class CountSession:
    """Counting Session"""
    
    def __init__(self, guild_id: int, voice_client, message: discord.Message):
        self.guild_id = guild_id
        self.voice_client = voice_client
        self.message = message  # Main counter card message
        self.is_running = False
        self.stop_requested = False
        self.current_number = 0
        self.task: Optional[asyncio.Task] = None
        
        # Message tracking (for deletion after 3 seconds)
        self.messages_to_delete: List[discord.Message] = []
        self.delete_task: Optional[asyncio.Task] = None
    
    def should_stop(self) -> bool:
        """Check if should stop"""
        return self.stop_requested
    
    def request_stop(self):
        """Request stop"""
        self.stop_requested = True
    
    def add_message_to_delete(self, message: discord.Message):
        """Add message to delete list"""
        if message not in self.messages_to_delete:
            self.messages_to_delete.append(message)
    
    def cancel_delete_task(self):
        """Cancel delete task"""
        if self.delete_task and not self.delete_task.done():
            self.delete_task.cancel()


class CountSessionManager:
    """Counting Session Manager"""
    
    def __init__(self):
        self._sessions: Dict[int, CountSession] = {}
    
    def create_session(self, guild_id: int, voice_client, 
                      message: discord.Message) -> CountSession:
        """Create new session"""
        session = CountSession(guild_id, voice_client, message)
        self._sessions[guild_id] = session
        return session
    
    def get_session(self, guild_id: int) -> Optional[CountSession]:
        """Get session"""
        return self._sessions.get(guild_id)
    
    def has_active_session(self, guild_id: int) -> bool:
        """Check for active session"""
        session = self._sessions.get(guild_id)
        return session is not None and session.is_running
    
    def cancel_session(self, guild_id: int):
        """Cancel session"""
        if guild_id in self._sessions:
            session = self._sessions[guild_id]
            if session.task and not session.task.done():
                session.task.cancel()
            del self._sessions[guild_id]

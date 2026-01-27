"""
Per-Message Discord Rate Limiter
Throttles updates for each message individually to prevent spam
while allowing concurrent updates to different messages
"""
import asyncio
import logging
from typing import Dict, Any, Optional
from datetime import datetime
import discord

logger = logging.getLogger(__name__)

class PerMessageThrottler:
    """
    Per-message throttle to prevent excessive updates to the same message
    Allows concurrent updates to different messages
    """
    
    def __init__(self, min_interval: float = 0.75):
        """
        Args:
            min_interval: Minimum seconds between updates for the same message (default 0.75s)
        """
        self.min_interval = min_interval
        self.last_update_times: Dict[int, float] = {}
        self.pending_updates: Dict[int, asyncio.Task] = {}
        self.locks: Dict[int, asyncio.Lock] = {}
        
    def _get_lock(self, message_id: int) -> asyncio.Lock:
        """Get or create lock for a message"""
        if message_id not in self.locks:
            self.locks[message_id] = asyncio.Lock()
        return self.locks[message_id]
    
    async def schedule_update(self, message: discord.Message, update_func, *args, **kwargs):
        """
        Schedule an update for a message with throttling
        
        Args:
            message: Discord Message to update
            update_func: Async function to call (e.g., message.edit)
            *args, **kwargs: Arguments for the function
        """
        message_id = message.id
        lock = self._get_lock(message_id)
        
        async with lock:
            # Cancel pending update for this message (only keep the latest)
            if message_id in self.pending_updates:
                old_task = self.pending_updates[message_id]
                if not old_task.done():
                    old_task.cancel()
                    try:
                        await old_task
                    except asyncio.CancelledError:
                        pass
            
            # Calculate wait time
            current_time = asyncio.get_event_loop().time()
            last_update = self.last_update_times.get(message_id, 0)
            time_since_last = current_time - last_update
            
            wait_time = max(0, self.min_interval - time_since_last)
            
            # Schedule the update
            task = asyncio.create_task(
                self._execute_update(message_id, wait_time, update_func, *args, **kwargs)
            )
            self.pending_updates[message_id] = task
    
    async def _execute_update(self, message_id: int, wait_time: float, update_func, *args, **kwargs):
        """Execute the update after wait time"""
        try:
            if wait_time > 0:
                await asyncio.sleep(wait_time)
            
            # Execute update
            await update_func(*args, **kwargs)
            
            # Record update time
            self.last_update_times[message_id] = asyncio.get_event_loop().time()
            
        except asyncio.CancelledError:
            # Update was cancelled by a newer update
            pass
        except discord.HTTPException as e:
            if e.status != 404:  # Ignore "Unknown Message" errors
                logger.error(f"Discord update failed: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in Discord update: {e}")
        finally:
            # Clean up
            if message_id in self.pending_updates:
                del self.pending_updates[message_id]

# Global instance (singleton)
_per_message_throttler = PerMessageThrottler(min_interval=0.75)

async def throttled_message_update(message: discord.Message, update_func, *args, **kwargs):
    """
    Public API: Schedule a throttled update for a Discord message
    
    Args:
        message: Discord Message object
        update_func: Async function to call (e.g., message.edit)
        *args, **kwargs: Arguments for the function
    
    Usage:
        await throttled_message_update(message, message.edit, embed=my_embed)
    """
    await _per_message_throttler.schedule_update(message, update_func, *args, **kwargs)

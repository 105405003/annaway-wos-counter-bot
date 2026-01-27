"""
Global Discord Rate Limiter
Ensures all Discord message edits are queued and executed sequentially
to prevent concurrent API calls that trigger rate limiting
"""
import asyncio
import logging
from typing import Callable, Any
from collections import deque
from datetime import datetime

logger = logging.getLogger(__name__)

class GlobalDiscordRateLimiter:
    """
    Global singleton to manage all Discord API calls
    Ensures updates are sequential with proper spacing
    """
    
    def __init__(self, min_interval: float = 0.2):
        """
        Args:
            min_interval: Minimum seconds between Discord API calls (default 0.2s = 5 calls/sec)
        """
        self.min_interval = min_interval
        self.queue = deque()
        self.processing = False
        self.last_call_time = 0.0
        self.lock = asyncio.Lock()
        
    async def schedule_update(self, update_func: Callable, *args, **kwargs):
        """
        Schedule a Discord update to be executed in the global queue
        
        Args:
            update_func: Async function to call
            *args, **kwargs: Arguments for the function
        """
        # Add to queue
        self.queue.append((update_func, args, kwargs))
        
        # Start processor if not running
        async with self.lock:
            if not self.processing:
                asyncio.create_task(self._process_queue())
    
    async def _process_queue(self):
        """Process the update queue sequentially"""
        async with self.lock:
            self.processing = True
        
        try:
            while self.queue:
                # Get next update
                update_func, args, kwargs = self.queue.popleft()
                
                # Enforce minimum interval
                current_time = asyncio.get_event_loop().time()
                time_since_last = current_time - self.last_call_time
                
                if time_since_last < self.min_interval:
                    await asyncio.sleep(self.min_interval - time_since_last)
                
                # Execute update
                try:
                    await update_func(*args, **kwargs)
                    self.last_call_time = asyncio.get_event_loop().time()
                except Exception as e:
                    logger.error(f"Discord update failed: {e}")
                
        finally:
            async with self.lock:
                self.processing = False

# Global instance (singleton)
_global_rate_limiter = GlobalDiscordRateLimiter(min_interval=0.25)

async def schedule_discord_update(update_func: Callable, *args, **kwargs):
    """
    Public API: Schedule a Discord update through the global rate limiter
    
    Usage:
        await schedule_discord_update(message.edit, embed=my_embed)
    """
    await _global_rate_limiter.schedule_update(update_func, *args, **kwargs)

"""
Discord Pink Card Management
Creates and updates Embed messages, handling rate limits
"""
import discord
import logging
from datetime import datetime
import asyncio
from typing import Optional, Dict
from collections import deque
from .timeops import format_countdown

logger = logging.getLogger(__name__)

# Pink Theme Color
REFILL_COLOR = 0xF97068

# Global Rate Limit Manager
class RateLimitManager:
    """Manages update queue to prevent rate limiting"""
    def __init__(self):
        self.update_queue: Dict[int, deque] = {}  # message_id -> queue of (name, remaining, retry_count)
        self.processing: Dict[int, bool] = {}  # message_id -> is_processing
        self.last_update_time: Dict[int, float] = {}  # message_id -> last update timestamp
        
    async def queue_update(self, message: discord.Message, name: str, remaining: int):
        """Add update to queue and process if not already processing"""
        msg_id = message.id
        
        # Initialize queue if needed
        if msg_id not in self.update_queue:
            self.update_queue[msg_id] = deque(maxlen=2)  # Keep only last 2 updates
            self.processing[msg_id] = False
        
        # Add to queue (if full, oldest update is dropped automatically)
        self.update_queue[msg_id].append((name, remaining, 0))
        
        # Start processing if not already processing
        if not self.processing[msg_id]:
            asyncio.create_task(self._process_queue(message))
    
    async def _process_queue(self, message: discord.Message):
        """Process update queue for a message"""
        msg_id = message.id
        self.processing[msg_id] = True
        
        try:
            while self.update_queue[msg_id]:
                # Get next update
                name, remaining, retry_count = self.update_queue[msg_id].popleft()
                
                # Rate limit: min 0.5s between updates for same message
                current_time = asyncio.get_event_loop().time()
                last_time = self.last_update_time.get(msg_id, 0)
                time_since_last = current_time - last_time
                
                if time_since_last < 0.5:
                    await asyncio.sleep(0.5 - time_since_last)
                
                # Perform update
                success = await _update_refill_card_direct(message, name, remaining, retry_count)
                
                # Record update time
                if success:
                    self.last_update_time[msg_id] = asyncio.get_event_loop().time()
                
        finally:
            self.processing[msg_id] = False

# Global instance
_rate_limit_manager = RateLimitManager()

async def create_refill_card(channel, name: str, remaining: int) -> Optional[discord.Message]:
    """
    Create Refill Timer Card
    
    Args:
        channel: Discord Channel (Text or Voice)
        name: Timer Name
        remaining: Remaining Seconds
        
    Returns:
        Created Message Object
    """
    embed = discord.Embed(
        title=f"[Refill] {name}",
        description=f"⏰ Remaining: {format_countdown(remaining)}",
        color=REFILL_COLOR
    )
    embed.set_footer(text="Refill Timer")
    
    try:
        message = await channel.send(embed=embed)
        logger.info(f"Created timer card: {name}")
        return message
    except Exception as e:
        logger.error(f"Failed to create card: {e}")
        return None

async def _update_refill_card_direct(message: discord.Message, name: str, remaining: int, retry_count: int = 0) -> bool:
    """
    Direct update (internal use, called by RateLimitManager)
    
    Args:
        message: Discord Message
        name: Timer Name
        remaining: Remaining Seconds
        retry_count: Current retry count
        
    Returns:
        Success boolean
    """
    if remaining <= 0:
        description = "🎯 **REFILL** 🎯"
    else:
        description = f"⏰ Remaining: {format_countdown(remaining)}"
    
    embed = discord.Embed(
        title=f"[Refill] {name}",
        description=description,
        color=REFILL_COLOR if remaining > 0 else 0x00FF00  # Green when done
    )
    embed.set_footer(text="Refill Timer" if remaining > 0 else "Finished!")
    
    try:
        await message.edit(embed=embed)
        return True
    except discord.HTTPException as e:
        if e.status == 429:  # Rate Limit
            if retry_count < 5:  # Increased max retries
                retry_after = 1.0
                try:
                    retry_after = float(e.response.headers.get('Retry-After', 1.0))
                except:
                    pass
                
                logger.warning(f"⚠️  Rate limited! Retrying in {retry_after}s (attempt {retry_count + 1}/5)")
                await asyncio.sleep(retry_after)
                return await _update_refill_card_direct(message, name, remaining, retry_count + 1)
            else:
                logger.error("❌ Failed to update card: Max retries reached")
                return False
        else:
            logger.error(f"❌ Failed to update card: HTTP {e.status} - {e}")
            return False
    except Exception as e:
        logger.error(f"❌ Unexpected error updating card: {e}")
        return False

async def update_refill_card(message: discord.Message, name: str, remaining: int) -> bool:
    """
    Update Refill Timer Card (queued with rate limit protection)
    
    Args:
        message: Discord Message
        name: Timer Name
        remaining: Remaining Seconds
        
    Returns:
        Always returns True (queued for async processing)
    """
    await _rate_limit_manager.queue_update(message, name, remaining)
    return True

async def delete_refill_card(message: discord.Message) -> bool:
    """
    Delete Refill Timer Card
    
    Args:
        message: Discord Message
        
    Returns:
        Success boolean
    """
    try:
        await message.delete()
        logger.info("Deleted timer card")
        return True
    except Exception as e:
        logger.error(f"Failed to delete card: {e}")
        return False

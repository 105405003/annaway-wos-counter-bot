"""
Discord Pink Card Management
Creates and updates Embed messages, handling rate limits
Uses global rate limiter for sequential updates
"""
import discord
import logging
from datetime import datetime
import asyncio
from typing import Optional
from .timeops import format_countdown
from .discord_rate_limiter import schedule_discord_update

logger = logging.getLogger(__name__)

# Pink Theme Color
REFILL_COLOR = 0xF97068

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

async def update_refill_card(message: discord.Message, name: str, remaining: int) -> bool:
    """
    Update Refill Timer Card (queued through global rate limiter)
    
    Args:
        message: Discord Message
        name: Timer Name
        remaining: Remaining Seconds
        
    Returns:
        Success boolean (always True - queued for async processing)
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
    
    # Schedule through global rate limiter (prevents concurrent updates)
    await schedule_discord_update(message.edit, embed=embed)
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

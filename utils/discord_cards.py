"""
Discord Pink Card Management
Creates and updates Embed messages, handling rate limits
"""
import discord
import logging
from datetime import datetime
import asyncio
from typing import Optional
from .timeops import format_countdown

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

async def update_refill_card(message: discord.Message, name: str, remaining: int, retry_count: int = 0) -> bool:
    """
    Update Refill Timer Card (with Rate Limit handling)
    
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
            if retry_count < 3:
                wait_time = float(e.response.headers.get('Retry-After', 1))
                logger.warning(f"Rate limited, retrying in {wait_time}s...")
                await asyncio.sleep(wait_time)
                return await update_refill_card(message, name, remaining, retry_count + 1)
            else:
                logger.error("Failed to update card: Max retries reached")
                return False
        else:
            logger.error(f"Failed to update card: {e}")
            return False
    except Exception as e:
        logger.error(f"Unexpected error updating card: {e}")
        return False

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

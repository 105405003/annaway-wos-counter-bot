"""
Image Streamer Module
Manages and updates number images in Discord messages
Uses pre-uploaded image URLs for fast updates without attachments
"""
import discord
import os
import asyncio
import logging
import json
from typing import Optional, Dict
from collections import deque
from .discord_rate_limiter import schedule_discord_update

logger = logging.getLogger(__name__)

class ImageStreamer:
    """Image Streamer Class"""
    
    def __init__(self, image_dir: str = 'assets/images'):
        self.image_dir = image_dir
        self.last_update_time = {}  # message_id -> last update timestamp
        self.update_lock = asyncio.Lock()  # Prevent concurrent updates
        self.image_urls: Dict[int, str] = {}  # number -> Discord image URL
        self._load_image_urls()
        
    def _load_image_urls(self):
        """Load pre-uploaded image URLs from JSON file"""
        url_file = 'assets/image_urls.json'
        try:
            if os.path.exists(url_file):
                with open(url_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    # Convert string keys to integers
                    self.image_urls = {int(k): v for k, v in data.items()}
                logger.info(f"✅ Loaded {len(self.image_urls)} pre-uploaded image URLs")
            else:
                logger.warning(f"⚠️  Image URLs file not found: {url_file}")
                logger.warning("   Run tools/upload_counter_images.py to create it")
        except Exception as e:
            logger.error(f"❌ Failed to load image URLs: {e}")
    
    def get_image_url(self, number: int) -> Optional[str]:
        """
        Get pre-uploaded image URL for a specific number
        
        Args:
            number: Number to display (0-100)
            
        Returns:
            Discord image URL or None
        """
        display_number = abs(number)
        return self.image_urls.get(display_number)
    
    def get_image_path(self, number: int) -> Optional[str]:
        """
        Get image path for a specific number
        Format: 000.png ~ 100.png
        """
        # Convert negative numbers to positive (for countdown)
        display_number = abs(number)
        
        # Format as 3-digit filename
        filename = f"{display_number:03d}.png"
        path = os.path.join(self.image_dir, filename)
        
        if os.path.exists(path):
            return path
        else:
            print(f"⚠️ Image not found: {path}")
            return None
    
    async def update_message_image(self, message: discord.Message, 
                                   number: int) -> bool:
        """
        Update image in the message using pre-uploaded URLs (queued through rate limiter)
        
        Args:
            message: Discord Message Object
            number: Number to display
            
        Returns:
            bool: Success (always True - queued)
        """
        # Get pre-uploaded image URL
        image_url = self.get_image_url(number)
        
        embed = discord.Embed(
            title="🔢 Counting in Progress",
            color=0x199E91  # Teal
        )
        
        if image_url:
            # Use pre-uploaded image URL (FAST - no attachment upload)
            embed.set_image(url=image_url)
            # Schedule through global rate limiter
            await schedule_discord_update(message.edit, embed=embed)
        else:
            # Fallback: try local file upload (slower, but shouldn't happen if images are pre-uploaded)
            image_path = self.get_image_path(number)
            if image_path:
                file = discord.File(image_path, filename=f"number.png")
                embed.set_image(url=f"attachment://number.png")
                await schedule_discord_update(message.edit, embed=embed, attachments=[file])
            else:
                # Last resort: text only
                embed.description = f"# {abs(number)}"
                await schedule_discord_update(message.edit, embed=embed)
        
        return True
    
    async def create_initial_message(self, channel: discord.TextChannel) -> discord.Message:
        """
        Create initial message
        """
        embed = discord.Embed(
            title="🔢 Counter Bot",
            description="Preparing to count...",
            color=0x199E91
        )
        return await channel.send(embed=embed)
    
    async def show_completion_message(self, message: discord.Message, 
                                     stopped_manually: bool = False,
                                     final_number: int = 100):
        """
        Show completion message
        """
        if stopped_manually:
            title = "⏹️ Stopped"
            description = f"Stopped at number **{final_number}**"
            color = 0xFF9800  # Orange
        else:
            title = "✅ Finished!"
            description = "Counted to **100**"
            color = 0x4CAF50  # Green
            
        embed = discord.Embed(
            title=title,
            description=description,
            color=color
        )
        
        try:
            await message.edit(embed=embed, attachments=[])
        except Exception as e:
            print(f"❌ Failed to update completion message: {e}")

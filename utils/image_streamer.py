"""
Image Streamer Module
Manages and updates number images in Discord messages
"""
import discord
import os
from typing import Optional

class ImageStreamer:
    """Image Streamer Class"""
    
    def __init__(self, image_dir: str = 'assets/images'):
        self.image_dir = image_dir
        
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
        Update image in the message
        
        Args:
            message: Discord Message Object
            number: Number to display
            
        Returns:
            bool: Success
        """
        image_path = self.get_image_path(number)
        
        try:
            if image_path:
                # Upload image if exists
                file = discord.File(image_path, filename=f"number.png")
                embed = discord.Embed(
                    title="🔢 Counting in Progress",
                    color=0x199E91  # Teal
                )
                embed.set_image(url=f"attachment://number.png")
                
                await message.edit(embed=embed, attachments=[file])
            else:
                # Fallback to text
                embed = discord.Embed(
                    title="🔢 Counting in Progress",
                    description=f"# {abs(number)}",
                    color=0x199E91
                )
                await message.edit(embed=embed, attachments=[])
                
            return True
            
        except discord.HTTPException as e:
            print(f"❌ Failed to update message: {e}")
            return False
        except Exception as e:
            print(f"❌ Unexpected error: {e}")
            return False
    
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

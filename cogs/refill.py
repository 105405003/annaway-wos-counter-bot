"""
Refill Timer Cog
Handles /refill panel command and Discord card management
"""
import discord
from discord.ext import commands
from discord import app_commands
import logging
import os
from typing import Optional
from utils.sessions import SessionManager
from utils.discord_cards import create_refill_card, update_refill_card, delete_refill_card
from datetime import datetime

logger = logging.getLogger(__name__)

class RefillTimer(commands.Cog):
    """Refill Timer Cog"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session_manager = SessionManager()
        self.target_channel_id = os.getenv('TARGET_TEXT_CHANNEL_ID')
        # Store the last channel ID where /refill was used for each Guild
        self.last_refill_channel_ids = {}
        
    async def get_target_channel(self, guild: discord.Guild) -> Optional[discord.TextChannel]:
        """Get target text channel"""
        if self.target_channel_id:
            try:
                channel = guild.get_channel(int(self.target_channel_id))
                if channel and isinstance(channel, discord.TextChannel):
                    return channel
            except:
                pass
        
        # Fallback: Use the first available text channel
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                return channel
        
        return None
    
    @app_commands.command(name="refill", description="Show Refill Timer Panel Info")
    async def refill_panel(self, interaction: discord.Interaction):
        """Show Refill Timer Info"""
        # Check permissions
        required_role = interaction.guild.get_role(1425481189443244123)
        if required_role and required_role not in interaction.user.roles:
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message(
                    "❌ You don't have permission to use this command!",
                    ephemeral=True
                )
                return
        
        # Record the channel ID used for /refill in this Guild (supports Text and Voice channels)
        if isinstance(interaction.channel, (discord.TextChannel, discord.VoiceChannel)):
            self.last_refill_channel_ids[interaction.guild_id] = interaction.channel.id
            channel_type = "Voice Channel" if isinstance(interaction.channel, discord.VoiceChannel) else "Text Channel"
            logger.info(f"✅ Recorded timer channel for Guild {interaction.guild.name}: {interaction.channel.name} ({channel_type}, ID: {interaction.channel.id})")
        
        # Get currently active timers
        guild_sessions = self.session_manager.get_guild_sessions(interaction.guild_id)
        active_timers = [s for s in guild_sessions.values() if s.status == "active"]
        
        embed = discord.Embed(
            title="🎯 Refill Timer Panel",
            description="Manage refill timers via the Web Panel",
            color=0xF97068
        )
        
        # Panel URL
        panel_url = os.getenv('PANEL_URL', 'https://tools.annaway.com.tw/wos/counter-bot/')
        embed.add_field(
            name="📱 Web Panel",
            value=f"[Click to Open]({panel_url})",
            inline=False
        )
        
        embed.add_field(
            name="📝 Instructions",
            value=(
                "1. Add a new timer in the Web Panel\n"
                "2. Timers will appear as pink cards in this channel\n"
                "3. Countdown starts immediately upon setup\n"
                "4. Shows **REFILL** when time is up"
            ),
            inline=False
        )
        
        embed.set_footer(text="Refill Timer System")
        
        await interaction.response.send_message(embed=embed)
    
    async def handle_timer_create(self, timer_id: str, guild_id: int, 
                                  name: str, remaining: int) -> Optional[str]:
        """
        Handle timer creation
        
        Args:
            timer_id: Timer ID
            guild_id: Guild ID
            name: Timer Name
            remaining: Remaining seconds
            
        Returns:
            Discord Message ID
        """
        guild = self.bot.get_guild(guild_id)
        if not guild:
            logger.error(f"❌ Guild not found: {guild_id}")
            return None
        
        # Prioritize the recorded channel (last channel where /refill was used)
        channel = None
        last_channel_id = self.last_refill_channel_ids.get(guild_id)
        
        if last_channel_id:
            channel = guild.get_channel(last_channel_id)
            # Support Text and Voice channels
            if channel and isinstance(channel, (discord.TextChannel, discord.VoiceChannel)):
                channel_type = "Voice Channel" if isinstance(channel, discord.VoiceChannel) else "Text Channel"
                logger.info(f"✅ Using recorded channel: {channel.name} ({channel_type}, ID: {channel.id})")
            else:
                logger.warning(f"⚠️ Recorded channel ID {last_channel_id} invalid, using default channel")
                channel = None
        
        if not channel:
            # If no record, use default channel
            logger.info(f"📝 No recorded channel, using default")
            channel = await self.get_target_channel(guild)
        
        if not channel:
            logger.error(f"❌ Target channel not found: {guild_id}")
            return None
        
        logger.info(f"🎯 Creating timer card in channel #{channel.name}")
        
        # Create Discord Card
        message = await create_refill_card(channel, name, remaining)
        if not message:
            return None
        
        # Save session
        t_end = datetime.now()  # Should be retrieved from backend
        session = self.session_manager.create_session(
            guild_id, timer_id, name, t_end, remaining
        )
        session.discord_message = message
        
        return str(message.id)
    
    async def handle_timer_tick(self, timer_id: str, guild_id: int, remaining: int):
        """
        Handle timer tick (updates every second within 60s)
        
        Args:
            timer_id: Timer ID
            guild_id: Guild ID
            remaining: Remaining seconds
        """
        session = self.session_manager.get_session(guild_id, timer_id)
        if not session or not session.discord_message:
            return
        
        await update_refill_card(session.discord_message, session.name, remaining)
    
    async def handle_timer_complete(self, timer_id: str, guild_id: int):
        """
        Handle timer completion
        
        Args:
            timer_id: Timer ID
            guild_id: Guild ID
        """
        session = self.session_manager.get_session(guild_id, timer_id)
        if not session or not session.discord_message:
            return
        
        # Update to REFILL
        await update_refill_card(session.discord_message, session.name, 0)
        session.status = "completed"
        
        logger.info(f"Timer completed: {timer_id}")
    
    async def handle_timer_delete(self, timer_id: str, guild_id: int):
        """
        Handle timer deletion
        
        Args:
            timer_id: Timer ID
            guild_id: Guild ID
        """
        session = self.session_manager.get_session(guild_id, timer_id)
        if not session:
            return
        
        # Delete Discord Message
        if session.discord_message:
            await delete_refill_card(session.discord_message)
        
        # Remove session
        self.session_manager.remove_session(guild_id, timer_id)
        
        logger.info(f"Timer deleted: {timer_id}")

async def setup(bot: commands.Bot):
    """Setup Cog"""
    await bot.add_cog(RefillTimer(bot))

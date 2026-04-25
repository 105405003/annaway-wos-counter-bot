"""
Counter Cog
Manages the counting bot functionality
"""
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
import logging
from typing import Optional

from utils import AudioPlayer, ImageStreamer, CountSessionManager
from utils.config import GUILD_ALLOWLIST, COUNTER_ROLE_IDS, COUNTER_ROLE_NAME

logger = logging.getLogger(__name__)

class CounterView(discord.ui.View):
    """Counter Control Panel View"""
    
    def __init__(self, cog: 'Counter'):
        super().__init__(timeout=None)
        self.cog = cog
        
    @discord.ui.button(label='Start', style=discord.ButtonStyle.success, emoji='▶️')
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Start Button"""
        # Check permissions
        if interaction.guild_id not in GUILD_ALLOWLIST:
            await interaction.response.send_message(
                "❌ This bot is not configured for this server.",
                ephemeral=True
            )
            return

        role_id = COUNTER_ROLE_IDS.get(interaction.guild_id)
        required_role = None
        if role_id:
            required_role = interaction.guild.get_role(role_id)
        
        if required_role is None:
            required_role = next(
                (r for r in interaction.guild.roles if r.name == COUNTER_ROLE_NAME),
                None
            )
            
        if required_role is None:
            await interaction.response.send_message(
                "❌ Error: Required role not found!\nPlease ask an admin to check role settings.",
                ephemeral=True
            )
            return

        if required_role not in interaction.user.roles and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ You don't have permission! Requires `Annaway_Counter` role.",
                ephemeral=True
            )
            return
            
        await interaction.response.defer()
        await self.cog.start_counting(interaction)
        
    @discord.ui.button(label='Stop', style=discord.ButtonStyle.danger, emoji='⏹️')
    async def stop_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Stop Button"""
        # Check permissions
        if interaction.guild_id not in GUILD_ALLOWLIST:
            await interaction.response.send_message(
                "❌ This bot is not configured for this server.",
                ephemeral=True
            )
            return

        role_id = COUNTER_ROLE_IDS.get(interaction.guild_id)
        required_role = None
        if role_id:
            required_role = interaction.guild.get_role(role_id)
            
        if required_role is None:
            required_role = next(
                (r for r in interaction.guild.roles if r.name == COUNTER_ROLE_NAME),
                None
            )
            
        if required_role is None:
            await interaction.response.send_message(
                "❌ Error: Required role not found!\nPlease ask an admin to check role settings.",
                ephemeral=True
            )
            return

        if required_role not in interaction.user.roles and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ You don't have permission! Requires `Annaway_Counter` role.",
                ephemeral=True
            )
            return
            
        await interaction.response.defer()
        await self.cog.stop_counting(interaction)


class Counter(commands.Cog):
    """Counting Bot Cog"""
    
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.session_manager = CountSessionManager()
        self.audio_player = AudioPlayer()
        self.image_streamer = ImageStreamer()
    
    async def _delete_messages_after_delay(self, session, seconds: int):
        """Delete tracked messages after delay"""
        import logging
        logger = logging.getLogger(__name__)
        
        await asyncio.sleep(seconds)
        
        for message in session.messages_to_delete:
            try:
                await message.delete()
                logger.info(f"✅ Deleted message: {message.id}")
            except discord.errors.NotFound:
                logger.warning(f"⚠️ Message not found: {message.id}")
            except discord.errors.Forbidden:
                logger.error(f"❌ Permission denied deleting message: {message.id}")
            except Exception as e:
                logger.error(f"❌ Failed to delete message ({message.id}): {e}")
    
    @app_commands.command(name="counter", description="Start the counting bot")
    async def counter_command(self, interaction: discord.Interaction):
        """Counter Command"""
        # Check permissions
        if interaction.guild_id not in GUILD_ALLOWLIST:
            await interaction.response.send_message(
                "❌ This bot is not configured for this server.",
                ephemeral=True
            )
            return

        role_id = COUNTER_ROLE_IDS.get(interaction.guild_id)
        required_role = None
        if role_id:
            required_role = interaction.guild.get_role(role_id)
            
        if required_role is None:
            required_role = next(
                (r for r in interaction.guild.roles if r.name == COUNTER_ROLE_NAME),
                None
            )
            
        if required_role is None:
            await interaction.response.send_message(
                "❌ Error: Required role not found!\nPlease ask an admin to check role settings.",
                ephemeral=True
            )
            return

        if required_role not in interaction.user.roles and not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ You don't have permission!\nRequires `Annaway_Counter` role to operate.",
                ephemeral=True
            )
            return
        
        embed = discord.Embed(
            title="🔢 Counter Bot",
            description="Click 'Start' to begin!\n\n"
                       "📢 Please join a Voice Channel first\n"
                       "🎵 Bot will count down 3→2→1→0\n"
                       "📈 Then count up 1→100\n"
                       "🖼️ Visuals will sync with numbers",
            color=0x199E91
        )
        
        view = CounterView(self)
        await interaction.response.send_message(embed=embed, view=view)
        
    async def start_counting(self, interaction: discord.Interaction):
        """Start Counting"""
        guild_id = interaction.guild_id
        
        # Check for active session (thread-safe check)
        existing_session = self.session_manager.get_session(guild_id)
        
        if existing_session and existing_session.is_running:
            # If running, deny restart
            await interaction.followup.send("⚠️ A counting session is already in progress!", ephemeral=True)
            return
        
        # If old session exists (waiting for cleanup), forcefully clean it up
        if existing_session:
            # Cancel any pending tasks
            existing_session.cancel_delete_task()
            if existing_session.task and not existing_session.task.done():
                existing_session.task.cancel()
                try:
                    await existing_session.task
                except asyncio.CancelledError:
                    pass
            
            # Disconnect old voice client
            if existing_session.voice_client and existing_session.voice_client.is_connected():
                try:
                    await existing_session.voice_client.disconnect()
                except:
                    pass
            
            # Clear old session completely
            self.session_manager.cancel_session(guild_id)
            await asyncio.sleep(0.3)  # Brief pause for cleanup
            
        # Check if user is in VC
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.followup.send("❌ Please join a Voice Channel first!", ephemeral=True)
            return
            
        voice_channel = interaction.user.voice.channel
        
        try:
            # Double-check guild voice client
            existing_voice_client = interaction.guild.voice_client
            
            if existing_voice_client:
                try:
                    await existing_voice_client.disconnect(force=True)
                    await asyncio.sleep(1.0)  # Longer wait for Discord to clean up
                except:
                    pass
            
            # Connect to VC with single attempt (disable auto-reconnect)
            voice_client = None
            max_retries = 1
            
            for attempt in range(max_retries):
                try:
                    voice_client = await asyncio.wait_for(
                        voice_channel.connect(reconnect=False),
                        timeout=8.0
                    )
                    break
                except asyncio.TimeoutError:
                    if attempt < max_retries - 1:
                        await interaction.followup.send(
                            f"⚠️ Voice connection timeout, retrying... ({attempt + 1}/{max_retries})",
                            ephemeral=True
                        )
                        await asyncio.sleep(2.0)
                    else:
                        raise Exception("Voice connection timeout after 3 attempts")
                except discord.errors.ClientException as e:
                    if "already connected" in str(e).lower():
                        # Force disconnect and retry
                        if interaction.guild.voice_client:
                            await interaction.guild.voice_client.disconnect(force=True)
                            await asyncio.sleep(1.5)
                        if attempt < max_retries - 1:
                            await asyncio.sleep(2.0)
                        else:
                            raise
                    else:
                        raise
            
            if not voice_client:
                raise Exception("Failed to connect to voice channel")
            
            # Create initial message
            message = await interaction.channel.send(
                embed=discord.Embed(
                    title="🔢 Getting Ready",
                    description="Connecting to Voice Channel...",
                    color=0x199E91
                )
            )
            
            # Create session and IMMEDIATELY set is_running = True (prevent race condition)
            session = self.session_manager.create_session(guild_id, voice_client, message)
            session.is_running = True  # Set IMMEDIATELY to prevent double-start
            
            # Send start message
            start_msg = await interaction.followup.send("✅ Started Counting!", ephemeral=False, wait=True)
            session.add_message_to_delete(start_msg)
            session.add_message_to_delete(message)
            
            # Create counting task
            session.task = asyncio.create_task(self._counting_loop(session))
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)
            # Clean up failed session
            self.session_manager.cancel_session(guild_id)
            
    async def stop_counting(self, interaction: discord.Interaction):
        """Stop Counting"""
        guild_id = interaction.guild_id
        session = self.session_manager.get_session(guild_id)
        
        if not session or not session.is_running:
            await interaction.followup.send("⚠️ No active counting session!", ephemeral=True)
            return
        
        # Check if already stop requested (prevent double-stop)
        if session.stop_requested:
            await interaction.followup.send("⚠️ Stop already requested!", ephemeral=True)
            return
            
        session.request_stop()
        
        # Send stop message
        stop_msg = await interaction.followup.send("⏹️ Stopping...", ephemeral=False, wait=True)
        session.add_message_to_delete(stop_msg)
        
    async def _counting_loop(self, session):
        """Main Counting Loop"""
        try:
            # Countdown: 3, 2, 1, 0
            for number in [3, 2, 1, 0]:
                if session.should_stop():
                    break
                
                # Image priority
                asyncio.create_task(
                    self.image_streamer.update_message_image(
                        session.message, 
                        number
                    )
                )
                
                # Audio sync
                asyncio.create_task(
                    self.audio_player.play_audio(
                        session.voice_client, 
                        number if number == 0 else -number
                    )
                )
                
                await asyncio.sleep(1.0)
            
            # Count up: 1 ~ 100
            for number in range(1, 101):
                if session.should_stop():
                    break
                    
                session.current_number = number
                
                # Image priority
                asyncio.create_task(
                    self.image_streamer.update_message_image(
                        session.message, 
                        number
                    )
                )
                
                # Audio sync
                asyncio.create_task(
                    self.audio_player.play_audio(
                        session.voice_client, 
                        number
                    )
                )
                
                await asyncio.sleep(1.0)
            
            # Show completion
            await self.image_streamer.show_completion_message(
                session.message,
                stopped_manually=session.stop_requested,
                final_number=abs(session.current_number)
            )
            
            # Start delete timer (3s)
            session.delete_task = asyncio.create_task(
                self._delete_messages_after_delay(session, 3)
            )
            
        except asyncio.CancelledError:
            print("🔴 Counting task cancelled")
        except Exception as e:
            print(f"❌ Counting loop error: {e}")
            try:
                await session.message.edit(
                    embed=discord.Embed(
                        title="❌ Error Occurred",
                        description=f"```{str(e)}```",
                        color=0xF44336
                    )
                )
            except:
                pass
        finally:
            # Cleanup (with safeguards)
            session.is_running = False
            
            # Check if this session is still the active one (not replaced by a new session)
            current_session = self.session_manager.get_session(guild_id)
            if current_session and current_session != session:
                # A new session has started, don't clean up
                print(f"⚠️ New session detected, skipping cleanup for old session")
                return
            
            # Wait 15s before leaving VC
            await asyncio.sleep(15)
            
            # Double-check before disconnecting
            current_session = self.session_manager.get_session(guild_id)
            if current_session and current_session != session:
                # New session started during sleep, don't disconnect
                print(f"⚠️ New session started, skipping VC disconnect")
                return
            
            if session.voice_client and session.voice_client.is_connected():
                try:
                    await session.voice_client.disconnect(force=True)
                    await asyncio.sleep(0.5)  # Wait for disconnect to complete
                except:
                    pass
                
            # Remove session only if it's still the current one
            if current_session == session:
                self.session_manager.cancel_session(session.guild_id)
            
            print(f"✅ Session cleanup complete (Guild: {session.guild_id})")

async def setup(bot: commands.Bot):
    """Setup Cog"""
    await bot.add_cog(Counter(bot))

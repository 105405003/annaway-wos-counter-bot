"""
Counter Cog
Manages the counting bot functionality
"""
import discord
from discord.ext import commands
from discord import app_commands
import asyncio
from typing import Optional

from utils import AudioPlayer, ImageStreamer, CountSessionManager

class CounterView(discord.ui.View):
    """Counter Control Panel View"""
    
    def __init__(self, cog: 'Counter'):
        super().__init__(timeout=None)
        self.cog = cog
        
    @discord.ui.button(label='Start', style=discord.ButtonStyle.success, emoji='▶️')
    async def start_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        """Start Button"""
        # Check permissions
        required_role = interaction.guild.get_role(1425481189443244123)
        if required_role is None or required_role not in interaction.user.roles:
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
        required_role = interaction.guild.get_role(1425481189443244123)
        if required_role is None or required_role not in interaction.user.roles:
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
        # Check if user has Annaway_Counter role
        required_role = interaction.guild.get_role(1425481189443244123)
        
        if required_role is None:
            # Role doesn't exist
            await interaction.response.send_message(
                "❌ Error: Required role not found!\n"
                "Please ask an admin to check role settings.",
                ephemeral=True
            )
            return
        
        if required_role not in interaction.user.roles:
            # User doesn't have role
            await interaction.response.send_message(
                "❌ You don't have permission!\n"
                "Requires `Annaway_Counter` role to operate.",
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
        
        # Check for active session
        existing_session = self.session_manager.get_session(guild_id)
        
        if existing_session and existing_session.is_running:
            # If running, deny restart
            await interaction.followup.send("⚠️ A counting session is already in progress!", ephemeral=True)
            return
        
        # If old session exists (waiting for cleanup), cancel cleanup
        if existing_session:
            existing_session.cancel_delete_task()
            existing_session.messages_to_delete.clear()
            
        # Check if user is in VC
        if not interaction.user.voice or not interaction.user.voice.channel:
            await interaction.followup.send("❌ Please join a Voice Channel first!", ephemeral=True)
            return
            
        voice_channel = interaction.user.voice.channel
        
        try:
            # Check if already in VC
            existing_voice_client = interaction.guild.voice_client
            
            if existing_voice_client:
                # Disconnect first
                await existing_voice_client.disconnect()
                await asyncio.sleep(0.5)
            
            # Connect to VC
            voice_client = await voice_channel.connect()
            
            # Create initial message
            message = await interaction.channel.send(
                embed=discord.Embed(
                    title="🔢 Getting Ready",
                    description="Connecting to Voice Channel...",
                    color=0x199E91
                )
            )
            
            # Create session
            session = self.session_manager.create_session(guild_id, voice_client, message)
            session.is_running = True
            
            # Send start message
            start_msg = await interaction.followup.send("✅ Started Counting!", ephemeral=False, wait=True)
            session.add_message_to_delete(start_msg)
            session.add_message_to_delete(message)
            
            # Create counting task
            session.task = asyncio.create_task(self._counting_loop(session))
            
        except Exception as e:
            await interaction.followup.send(f"❌ Error: {e}", ephemeral=True)
            
    async def stop_counting(self, interaction: discord.Interaction):
        """Stop Counting"""
        guild_id = interaction.guild_id
        session = self.session_manager.get_session(guild_id)
        
        if not session or not session.is_running:
            await interaction.followup.send("⚠️ No active counting session!", ephemeral=True)
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
            await session.message.edit(
                embed=discord.Embed(
                    title="❌ Error Occurred",
                    description=f"```{str(e)}```",
                    color=0xF44336
                )
            )
        finally:
            # Cleanup
            session.is_running = False
            
            # Wait 15s before leaving VC
            await asyncio.sleep(15)
            
            if session.voice_client and session.voice_client.is_connected():
                await session.voice_client.disconnect()
                
            # Remove session
            self.session_manager.cancel_session(session.guild_id)
            
            print(f"✅ Session cleanup complete (Guild: {session.guild_id})")

async def setup(bot: commands.Bot):
    """Setup Cog"""
    await bot.add_cog(Counter(bot))

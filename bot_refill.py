"""
Discord Bot Main Program - Refill Timer Integration
Starts both Discord Bot and FastAPI Backend
"""
import discord
from discord.ext import commands
import os
from dotenv import load_dotenv
import asyncio
import logging
import uvicorn
from threading import Thread
from utils.config import GUILD_ALLOWLIST, PORT

# Load Environment Variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FFmpeg uses system installed version
# If custom path is needed, set it here

# Setup Bot Intents
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.guilds = True

# Create Bot Instance
bot = commands.Bot(command_prefix='!', intents=intents)

# Store reference to refill cog
refill_cog = None

@bot.event
async def on_ready():
    logger.info(f'✅ Bot logged in as {bot.user}')
    logger.info(f'✅ Connected to {len(bot.guilds)} guilds')
    
    # Sync Slash Commands (Guild specific for immediate update)
    try:
        # First sync globally to ensure commands are registered
        global_synced = await bot.tree.sync()
        logger.info(f'✅ Synced {len(global_synced)} slash commands globally')
        
        # Then sync to specific guilds in allowlist for immediate availability
        for guild in bot.guilds:
            if guild.id in GUILD_ALLOWLIST:
                # 先把全域指令複製到這個 guild，指令才會立即顯示
                bot.tree.copy_global_to(guild=discord.Object(id=guild.id))
                guild_synced = await bot.tree.sync(guild=discord.Object(id=guild.id))
                logger.info(f'✅ Synced {len(guild_synced)} slash commands for guild {guild.name}')
    except Exception as e:
        logger.error(f'❌ Command sync failed: {e}', exc_info=True)
    
    # Set Bot Status
    await bot.change_presence(activity=discord.Game(name="Refill Timer | /refill"))

async def discord_callback(action: str, *args):
    """
    Discord Bot Callback Function
    Called by FastAPI backend to update Discord messages
    """
    global refill_cog
    
    if not refill_cog:
        return None
    
    try:
        # Parse args
        if action == "timer_create":
            timer_id = args[0]
            # Get timer info from backend
            from panel.backend.main import get_timer
            timer = get_timer(timer_id)
            if not timer:
                return None
            
            # Use the first guild in GUILD_ALLOWLIST (not just any guild)
            guild_id = None
            for guild in bot.guilds:
                if guild.id in GUILD_ALLOWLIST:
                    guild_id = guild.id
                    break
            
            if not guild_id:
                logger.error("❌ No guild found in GUILD_ALLOWLIST")
                return None
            
            return await refill_cog.handle_timer_create(
                timer_id, guild_id, timer['name'], 
                timer.get('total_seconds', 0)
            )
            
        elif action == "timer_tick":
            timer_id, remaining = args[0], args[1]
            # Use the first guild in GUILD_ALLOWLIST
            guild_id = None
            for guild in bot.guilds:
                if guild.id in GUILD_ALLOWLIST:
                    guild_id = guild.id
                    break
            if guild_id:
                await refill_cog.handle_timer_tick(timer_id, guild_id, remaining)
                
        elif action == "timer_complete":
            timer_id = args[0]
            # Use the first guild in GUILD_ALLOWLIST
            guild_id = None
            for guild in bot.guilds:
                if guild.id in GUILD_ALLOWLIST:
                    guild_id = guild.id
                    break
            if guild_id:
                await refill_cog.handle_timer_complete(timer_id, guild_id)
                
        elif action == "timer_delete":
            timer_id = args[0]
            # Use the first guild in GUILD_ALLOWLIST
            guild_id = None
            for guild in bot.guilds:
                if guild.id in GUILD_ALLOWLIST:
                    guild_id = guild.id
                    break
            if guild_id:
                await refill_cog.handle_timer_delete(timer_id, guild_id)
                
    except Exception as e:
        logger.error(f"Discord callback error: {e}")
        return None

async def load_cogs():
    """Load all Cogs"""
    global refill_cog
    
    # Load counter cog
    try:
        await bot.load_extension('cogs.counter')
        logger.info('✅ Loaded counter cog')
    except Exception as e:
        logger.error(f'❌ Failed to load counter cog: {e}')
    
    # Load refill cog
    try:
        await bot.load_extension('cogs.refill')
        refill_cog = bot.get_cog('RefillTimer')
        logger.info('✅ Loaded refill cog')
    except Exception as e:
        logger.error(f'❌ Failed to load refill cog: {e}')

async def start_bot():
    """Start Discord Bot"""
    async with bot:
        await load_cogs()
        await bot.start(TOKEN)

def start_fastapi():
    """Start FastAPI in a separate thread"""
    from panel.backend.main import app, set_discord_callback
    
    # Sync wrapper for Discord callback
    def sync_discord_callback(action: str, *args):
        """Sync wrapper to be called by FastAPI thread"""
        try:
            # Run async callback in Bot's event loop
            future = asyncio.run_coroutine_threadsafe(
                discord_callback(action, *args), 
                bot.loop
            )
            # Wait for result (max 10s)
            result = future.result(timeout=10)
            return result
        except Exception as e:
            logger.error(f"Sync callback execution failed: {e}", exc_info=True)
            return None
    
    # Set Discord callback
    set_discord_callback(sync_discord_callback)
    
    # Start FastAPI
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=PORT,
        log_level="info",
        loop="asyncio"
    )
    server = uvicorn.Server(config)
    server.run()

if __name__ == '__main__':
    # Ensure directories exist
    os.makedirs('assets/audio', exist_ok=True)
    os.makedirs('assets/images', exist_ok=True)
    
    logger.info("Starting Discord Bot and FastAPI Backend...")
    
    # Start FastAPI in separate thread
    fastapi_thread = Thread(target=start_fastapi, daemon=True)
    fastapi_thread.start()
    logger.info("✅ FastAPI backend started in background")
    
    # Start Discord Bot
    try:
        asyncio.run(start_bot())
    except KeyboardInterrupt:
        logger.info("Shutting down...")

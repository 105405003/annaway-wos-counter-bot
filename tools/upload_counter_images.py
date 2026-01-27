"""
Upload all counter images to Discord and save URLs
Run once to prepare image URLs for fast counter updates
"""
import discord
from discord.ext import commands
import asyncio
import os
import json
from dotenv import load_dotenv

load_dotenv()

# Configuration
TOKEN = os.getenv('DISCORD_TOKEN')
CHANNEL_ID = int(os.getenv('IMAGE_UPLOAD_CHANNEL_ID', '1353411026556817560'))
IMAGE_DIR = 'assets/images'
OUTPUT_FILE = 'assets/image_urls.json'

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

@bot.event
async def on_ready():
    print(f'✅ Logged in as {bot.user}')
    print(f'📤 Uploading images to channel ID: {CHANNEL_ID}')
    
    channel = bot.get_channel(CHANNEL_ID)
    if not channel:
        print(f'❌ Channel {CHANNEL_ID} not found!')
        await bot.close()
        return
    
    image_urls = {}
    
    try:
        # Upload images 0-100
        for number in range(101):
            filename = f"{number:03d}.png"
            filepath = os.path.join(IMAGE_DIR, filename)
            
            if not os.path.exists(filepath):
                print(f'⚠️  Image not found: {filepath}')
                continue
            
            # Upload image
            file = discord.File(filepath, filename=f"counter_{number}.png")
            
            # Send to channel with embed
            embed = discord.Embed(
                title=f"Counter Image {number}",
                description=f"Pre-uploaded for fast updates",
                color=0x199E91
            )
            embed.set_image(url=f"attachment://counter_{number}.png")
            
            message = await channel.send(embed=embed, file=file)
            
            # Extract image URL from the message
            if message.embeds and message.embeds[0].image:
                image_url = message.embeds[0].image.url
                image_urls[str(number)] = image_url
                print(f'✅ Uploaded {number}: {image_url}')
            else:
                print(f'❌ Failed to get URL for {number}')
            
            # Rate limit: wait 1 second between uploads
            await asyncio.sleep(1.0)
        
        # Save URLs to JSON file
        os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
        with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(image_urls, f, indent=2, ensure_ascii=False)
        
        print(f'\n🎉 Successfully uploaded {len(image_urls)} images!')
        print(f'💾 URLs saved to: {OUTPUT_FILE}')
        
    except Exception as e:
        print(f'❌ Error: {e}')
    
    finally:
        await bot.close()

if __name__ == '__main__':
    if not TOKEN:
        print('❌ DISCORD_TOKEN not found in .env file!')
        exit(1)
    
    print('Starting image upload process...')
    print('This will take about 2-3 minutes.')
    bot.run(TOKEN)

import os
from dotenv import load_dotenv

load_dotenv()  # Load environment variables

def parse_mapping(var_name: str) -> dict[int, int]:
    """Convert string 'guild_id:val,guild_id2:val2' to dict"""
    mapping: dict[int, int] = {}
    value = os.getenv(var_name, '')
    if value:
        pairs = [p.strip() for p in value.split(',') if ':' in p]
        for pair in pairs:
            try:
                guild, val = pair.split(':', 1)
                mapping[int(guild.strip())] = int(val.strip())
            except ValueError:
                continue
    return mapping

# Allowed Guild IDs
GUILD_ALLOWLIST = [int(g.strip()) for g in os.getenv('GUILD_ALLOWLIST', '').split(',') if g.strip()]

# Guild ID -> Role ID mapping
COUNTER_ROLE_IDS: dict[int, int] = parse_mapping('COUNTER_ROLE_IDS')

# Guild ID -> Text Channel ID mapping
TARGET_TEXT_CHANNEL_IDS: dict[int, int] = parse_mapping('TARGET_TEXT_CHANNEL_IDS')

# Fallback Role Name
COUNTER_ROLE_NAME = os.getenv('COUNTER_ROLE_NAME', 'Annaway_Counter')

# Web Panel URL
PANEL_URL = os.getenv('PANEL_URL', 'https://tools.annaway.com.tw/wos/counter-bot/')

# Port
PORT = int(os.getenv('PORT', 8001))


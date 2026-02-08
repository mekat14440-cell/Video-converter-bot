"""
Configuration file for the Telegram Streaming Bot.
All sensitive data is loaded from environment variables.

SETUP INSTRUCTIONS:
1. Go to https://my.telegram.org and create an app to get API_ID and API_HASH
2. Create a bot via @BotFather on Telegram to get BOT_TOKEN
3. Create a private channel for logging, add the bot as admin, get the channel ID
4. Set these as environment variables on Render

Environment Variables Required:
- API_ID: Your Telegram API ID (integer)
- API_HASH: Your Telegram API Hash (string)
- BOT_TOKEN: Your Bot Token from BotFather (string)
- LOG_CHANNEL: Channel ID where files will be stored (integer, e.g., -1001234567890)
- FQDN: Your Render app URL without https:// (e.g., my-app.onrender.com)
- PORT: Port number (Render provides this automatically)
"""

import os
from typing import Optional

# =============================================================================
# TELEGRAM API CREDENTIALS
# Get these from https://my.telegram.org/apps
# =============================================================================
API_ID: int = int(os.environ.get("API_ID", 0))
API_HASH: str = os.environ.get("API_HASH", "")

# =============================================================================
# BOT TOKEN
# Get this from @BotFather on Telegram
# =============================================================================
BOT_TOKEN: str = os.environ.get("BOT_TOKEN", "")

# =============================================================================
# LOG CHANNEL
# Create a private channel, add bot as admin, get channel ID
# The ID usually starts with -100
# =============================================================================
LOG_CHANNEL: int = int(os.environ.get("LOG_CHANNEL", 0))

# =============================================================================
# SERVER CONFIGURATION
# =============================================================================
# Port for the web server (Render provides PORT automatically)
PORT: int = int(os.environ.get("PORT", 8080))

# Your Render app domain (without https://)
# Example: "my-stream-bot.onrender.com"
FQDN: str = os.environ.get("FQDN", "localhost")

# Use HTTPS protocol (set to True for production on Render)
USE_HTTPS: bool = os.environ.get("USE_HTTPS", "True").lower() == "true"

# =============================================================================
# STREAMING CONFIGURATION
# =============================================================================
# Chunk size for streaming (1MB is optimal for most cases)
CHUNK_SIZE: int = 1024 * 1024  # 1 MB

# Maximum concurrent streams allowed
MAX_CONCURRENT_STREAMS: int = 50

# =============================================================================
# VALIDATION
# =============================================================================
def validate_config() -> bool:
    """Validate that all required configuration is set."""
    errors = []
    
    if API_ID == 0:
        errors.append("API_ID is not set")
    if not API_HASH:
        errors.append("API_HASH is not set")
    if not BOT_TOKEN:
        errors.append("BOT_TOKEN is not set")
    if LOG_CHANNEL == 0:
        errors.append("LOG_CHANNEL is not set")
    if FQDN == "localhost":
        errors.append("FQDN is not set (using localhost as default)")
    
    if errors:
        print("Configuration Errors:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    return True


def get_base_url() -> str:
    """Get the base URL for streaming links."""
    protocol = "https" if USE_HTTPS else "http"
    return f"{protocol}://{FQDN}"


# Print config status on import (useful for debugging)
if __name__ == "__main__":
    print("Configuration Status:")
    print(f"  API_ID: {'Set' if API_ID else 'Not Set'}")
    print(f"  API_HASH: {'Set' if API_HASH else 'Not Set'}")
    print(f"  BOT_TOKEN: {'Set' if BOT_TOKEN else 'Not Set'}")
    print(f"  LOG_CHANNEL: {LOG_CHANNEL}")
    print(f"  PORT: {PORT}")
    print(f"  FQDN: {FQDN}")
    print(f"  Base URL: {get_base_url()}")
    validate_config()

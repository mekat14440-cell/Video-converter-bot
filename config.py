"""
Configuration file for the Telegram Streaming Bot.
"""

import os
from typing import Optional

# =============================================================================
# TELEGRAM API CREDENTIALS
# =============================================================================
# আমি এখানে os.environ.get সরিয়ে সরাসরি আপনার ID বসিয়ে দিয়েছি
API_ID: int = 33544357

# এখানে আপনার HASH স্ট্রিং হিসেবে দেওয়া হলো
API_HASH: str = "15d6b65c6006e8c869534c047e305566"

# =============================================================================
# BOT TOKEN
# =============================================================================
BOT_TOKEN: str = "8328109785:AAEY5Xl0cAPkWJiDSPcpLtSkoNCUpwpPKLM"

# =============================================================================
# LOG CHANNEL
# =============================================================================
LOG_CHANNEL: int = -1003474155119

# =============================================================================
# SERVER CONFIGURATION
# =============================================================================
# Port for the web server (Render provides PORT automatically)
PORT: int = int(os.environ.get("PORT", 8080))

# Your Render app domain (without https://)
# Example: "my-stream-bot.onrender.com"
# আপনি চাইলে এখানে আপনার অ্যাপের নাম সরাসরি বসাতে পারেন, যেমন: "my-app.onrender.com"
FQDN: str = os.environ.get("FQDN", "localhost")

# Use HTTPS protocol (set to True for production on Render)
USE_HTTPS: bool = os.environ.get("USE_HTTPS", "True").lower() == "true"

# =============================================================================
# STREAMING CONFIGURATION
# =============================================================================
CHUNK_SIZE: int = 1024 * 1024  # 1 MB
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
    print(f"  API_ID: {API_ID}")
    print(f"  API_HASH: {'Set' if API_HASH else 'Not Set'}")
    print(f"  BOT_TOKEN: {'Set' if BOT_TOKEN else 'Not Set'}")
    print(f"  LOG_CHANNEL: {LOG_CHANNEL}")
    print(f"  PORT: {PORT}")
    print(f"  FQDN: {FQDN}")
    print(f"  Base URL: {get_base_url()}")
    validate_config()
    

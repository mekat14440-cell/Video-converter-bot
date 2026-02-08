"""
Configuration file - Fixed for Render (No Button Error)
"""

import os
from typing import Optional

# =============================================================================
# TELEGRAM CREDENTIALS (Your Data)
# =============================================================================
API_ID: int = 33544357
API_HASH: str = "15d6b65c6006e8c869534c047e305566"
BOT_TOKEN: str = "8328109785:AAEY5Xl0cAPkWJiDSPcpLtSkoNCUpwpPKLM"
LOG_CHANNEL: int = -1003474155119

# =============================================================================
# SERVER CONFIG (Critical Fixes)
# =============================================================================
PORT: int = int(os.environ.get("PORT", 8080))

# Set your Render app domain here (e.g., mystreambot.onrender.com)
FQDN: str = os.environ.get("FQDN", "localhost")

# FREE TIER FIX: Use HTTP instead of HTTPS to avoid BUTTON_URL_INVALID error
USE_HTTPS: bool = os.environ.get("USE_HTTPS", "False").lower() == "true"

# =============================================================================
# STREAMING CONFIG
# =============================================================================
CHUNK_SIZE: int = 1024 * 1024  # 1 MB
MAX_CONCURRENT_STREAMS: int = 50

# =============================================================================
# VALIDATION (Fixed)
# =============================================================================
def validate_config() -> bool:
    """Validate all required settings"""
    errors = []
    
    if API_ID == 0: errors.append("API_ID not set")
    if not API_HASH: errors.append("API_HASH not set")
    if not BOT_TOKEN: errors.append("BOT_TOKEN not set")
    if LOG_CHANNEL == 0: errors.append("LOG_CHANNEL not set")
    if FQDN == "localhost": errors.append("FQDN not set (Set in Render Environment!)")
    
    if errors:
        print("Configuration Errors:")
        for error in errors: print(f"  - {error}")
        return False
    
    return True


def get_base_url() -> str:
    """Get base URL for streaming links"""
    protocol = "http" if not USE_HTTPS else "https"
    return f"{protocol}://{FQDN}"


# Debug output
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

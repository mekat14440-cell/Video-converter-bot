"""
Configuration file - Updated for Render Free Tier (No Button Error)
"""

import os

# =============================================================================
# TELEGRAM CREDENTIALS (Tumhare diye hue)
# =============================================================================
API_ID: int = 33544357
API_HASH: str = "15d6b65c6006e8c869534c047e305566"
BOT_TOKEN: str = "8328109785:AAEY5Xl0cAPkWJiDSPcpLtSkoNCUpwpPKLM"
LOG_CHANNEL: int = -1003474155119

# =============================================================================
# SERVER CONFIG (Important Changes)
# =============================================================================
PORT: int = int(os.environ.get("PORT", 8080))

# Tumhara Render app ka naam daal do (jaise: mystreambot.onrender.com)
# Ya phir environment variable se le lo
FQDN: str = os.environ.get("FQDN", "localhost")  # Render pe FQDN set karna mat bhoolna!

# FREE TIER FIX: HTTP use karo, HTTPS button error deta hai!
USE_HTTPS: bool = False   # ← Yeh sabse important change hai!

# =============================================================================
# STREAMING
# =============================================================================
CHUNK_SIZE: int = 1024 * 1024  # 1MB

def get_base_url() -> str:
    """Always use HTTP on Render free tier to avoid BUTTON_URL_INVALID"""
    protocol = "http" if not USE_HTTPS else "https"
    return f"{protocol}://{FQDN}"

# Auto validation
if FQDN == "localhost":
    print("Warning: FQDN not set! Set it in Render environment variables!")
    print("Example: mystreambot.onrender.com")

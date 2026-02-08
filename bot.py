"""
Main Bot File - Initializes Pyrogram Client and Aiohttp Web Server.
"""

import asyncio
import logging
import sys
from typing import Optional

# Third-party imports
from aiohttp import web
from pyrogram import Client, idle

# Local imports
import config
from server.stream_routes import setup_routes

# =============================================================================
# LOGGING SETUP
# =============================================================================
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# =============================================================================
# GLOBAL INSTANCES
# =============================================================================
bot_client: Optional[Client] = None
web_app: Optional[web.Application] = None


def create_bot_client() -> Client:
    """Create and configure the Pyrogram bot client."""
    return Client(
        name="StreamBot",
        api_id=config.API_ID,
        api_hash=config.API_HASH,
        bot_token=config.BOT_TOKEN,
        plugins=dict(root="plugins"),
        workers=8,
        sleep_threshold=60,
    )


async def start_web_server(app: web.Application, port: int) -> web.TCPSite:
    """Start the aiohttp web server."""
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Bind to 0.0.0.0 to accept connections from anywhere
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()
    
    return site


async def main():
    """Main entry point - starts both the bot and web server."""
    global bot_client, web_app
    
    # Validate configuration
    if not config.validate_config():
        logger.error("Invalid configuration. Please check your environment variables.")
        return  # Exit gracefully

    logger.info("=" * 50)
    logger.info("Starting Telegram Stream Bot")
    logger.info("=" * 50)
    
    # Create the Pyrogram client
    bot_client = create_bot_client()
    
    # Create the web application
    web_app = web.Application(client_max_size=0)
    web_app["bot_client"] = bot_client
    
    # Setup routes
    # Note: Ensure you have the folder 'server' and file 'stream_routes.py'
    try:
        setup_routes(web_app)
    except Exception as e:
        logger.warning(f"Could not setup routes (Is server/stream_routes.py missing?): {e}")

    try:
        # Start the Pyrogram client
        await bot_client.start()
        
        bot_info = await bot_client.get_me()
        logger.info(f"Bot started: @{bot_info.username}")
        
        # Start the web server
        await start_web_server(web_app, config.PORT)
        logger.info(f"Web server started on port {config.PORT}")
        
        logger.info("=" * 50)
        logger.info("Bot is running! Press Ctrl+C to stop.")
        logger.info("=" * 50)
        
        # Keep the bot running
        await idle()
        
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
    finally:
        logger.info("Shutting down...")
        if bot_client:
            try:
                await bot_client.stop()
            except:
                pass
        logger.info("Goodbye!")


# =============================================================================
# ENTRY POINT (UPDATED)
# =============================================================================
if __name__ == "__main__":
    # uvloop setup for Linux/Render
    try:
        import uvloop
        uvloop.install()
        logger.info("Using uvloop for better performance")
    except ImportError:
        logger.info("uvloop not available, using default event loop")

    # Fixed: Using asyncio.run() instead of get_event_loop()
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        

"""
Main Bot File - 100% Fixed for Render (No Errors)
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
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# =============================================================================
# GLOBAL INSTANCES
# =============================================================================
bot_client: Optional[Client] = None
web_app: Optional[web.Application] = None


def create_bot_client() -> Client:
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
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()
    return site


async def main():
    """Main entry point - starts both bot and web server"""
    global bot_client, web_app
    
    # Validate configuration
    if not config.validate_config():
        logger.error("Invalid configuration. Exiting.")
        sys.exit(1)
    
    logger.info("=" * 50)
    logger.info("Starting Telegram Stream Bot")
    logger.info("=" * 50)
    
    # Initialize clients
    bot_client = create_bot_client()
    web_app = web.Application(client_max_size=0)
    web_app["bot_client"] = bot_client
    
    # Setup routes
    try:
        setup_routes(web_app)
    except Exception as e:
        logger.error(f"Failed to setup routes: {e}")
        sys.exit(1)
    
    try:
        # Start Pyrogram client
        await bot_client.start()
        bot_info = await bot_client.get_me()
        logger.info(f"Bot started: @{bot_info.username}")
        
        # Verify log channel access
        try:
            await bot_client.get_chat(config.LOG_CHANNEL)
            logger.info(f"Log channel verified: {config.LOG_CHANNEL}")
        except Exception as e:
            logger.error(f"Cannot access log channel: {e}")
            await bot_client.stop()
            sys.exit(1)
        
        # Start web server
        await start_web_server(web_app, config.PORT)
        logger.info(f"Web server started on port {config.PORT}")
        logger.info(f"Stream URL base: {config.get_base_url()}")
        
        logger.info("=" * 50)
        logger.info("Bot is running! Press Ctrl+C to stop.")
        logger.info("=" * 50)
        
        await idle()
        
    except KeyboardInterrupt:
        logger.info("Received shutdown signal")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
    finally:
        logger.info("Shutting down...")
        if bot_client:
            await bot_client.stop()
        logger.info("Goodbye!")


# =============================================================================
# ENTRY POINT (Fixed Event Loop)
# =============================================================================
if __name__ == "__main__":
    logger.info("Using default event loop (uvloop removed for stability)")
    asyncio.run(main())

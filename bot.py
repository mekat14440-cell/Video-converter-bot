"""
Main Bot File - Initializes Pyrogram Client and Aiohttp Web Server.

This is the entry point of the application. It:
1. Creates and starts the Pyrogram bot client
2. Starts the aiohttp web server for streaming
3. Handles graceful shutdown

Run this file to start the bot:
    python bot.py
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
# The Pyrogram client instance (will be initialized in main())
bot_client: Optional[Client] = None

# The aiohttp web application
web_app: Optional[web.Application] = None


def create_bot_client() -> Client:
    """
    Create and configure the Pyrogram bot client.
    
    Returns:
        Client: Configured Pyrogram client instance
    """
    return Client(
        name="StreamBot",
        api_id=config.API_ID,
        api_hash=config.API_HASH,
        bot_token=config.BOT_TOKEN,
        plugins=dict(root="plugins"),  # Load plugins from 'plugins' folder
        workers=8,  # Number of worker threads
        sleep_threshold=60,  # Sleep threshold for flood wait
    )


async def start_web_server(app: web.Application, port: int) -> web.TCPSite:
    """
    Start the aiohttp web server.
    
    Args:
        app: The aiohttp web application
        port: Port number to listen on
        
    Returns:
        web.TCPSite: The running web server site
    """
    runner = web.AppRunner(app)
    await runner.setup()
    
    # Bind to 0.0.0.0 to accept connections from anywhere (required for Render)
    site = web.TCPSite(runner, host="0.0.0.0", port=port)
    await site.start()
    
    return site


async def main():
    """
    Main entry point - starts both the bot and web server.
    """
    global bot_client, web_app
    
    # Validate configuration
    if not config.validate_config():
        logger.error("Invalid configuration. Please check your environment variables.")
        sys.exit(1)
    
    logger.info("=" * 50)
    logger.info("Starting Telegram Stream Bot")
    logger.info("=" * 50)
    
    # Create the Pyrogram client
    bot_client = create_bot_client()
    
    # Create the web application
    web_app = web.Application(
        client_max_size=0  # Disable body size limit
    )
    
    # Store bot client in app for access in route handlers
    web_app["bot_client"] = bot_client
    
    # Setup routes
    setup_routes(web_app)
    
    try:
        # Start the Pyrogram client
        await bot_client.start()
        
        bot_info = await bot_client.get_me()
        logger.info(f"Bot started: @{bot_info.username}")
        logger.info(f"Bot ID: {bot_info.id}")
        
        # Test LOG_CHANNEL access
        try:
            await bot_client.get_chat(config.LOG_CHANNEL)
            logger.info(f"Log channel verified: {config.LOG_CHANNEL}")
        except Exception as e:
            logger.error(f"Cannot access LOG_CHANNEL: {e}")
            logger.error("Make sure the bot is an admin in the log channel!")
            await bot_client.stop()
            sys.exit(1)
        
        # Start the web server
        await start_web_server(web_app, config.PORT)
        logger.info(f"Web server started on port {config.PORT}")
        logger.info(f"Stream URL base: {config.get_base_url()}")
        
        logger.info("=" * 50)
        logger.info("Bot is running! Press Ctrl+C to stop.")
        logger.info("=" * 50)
        
        # Keep the bot running
        await idle()
        
    except KeyboardInterrupt:
        logger.info("Received shutdown signal...")
    except Exception as e:
        logger.exception(f"Fatal error: {e}")
    finally:
        # Cleanup
        logger.info("Shutting down...")
        if bot_client:
            await bot_client.stop()
        logger.info("Goodbye!")


# =============================================================================
# ENTRY POINT
# =============================================================================
if __name__ == "__main__":
    # Use uvloop for better performance if available
    try:
        import uvloop
        uvloop.install()
        logger.info("Using uvloop for better performance")
    except ImportError:
        logger.info("uvloop not available, using default event loop")
    
    # Run the main function
    asyncio.get_event_loop().run_until_complete(main())

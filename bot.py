"""
Final Working Bot.py - No Uvloop, No Event Loop Errors
"""

import asyncio
import logging
import sys
from aiohttp import web
from pyrogram import Client, idle

# Local imports
import config
from server.stream_routes import setup_routes

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# Global Instances
bot_client = None
web_app = None

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
    global bot_client, web_app
    
    # Config Check
    if config.FQDN == "localhost":
        logger.error("FQDN not set! Please set it in Render environment variables!")
        sys.exit(1)
    
    logger.info("Starting Stream Bot...")
    
    # Create Bot Client
    bot_client = create_bot_client()
    
    # Create Web App
    web_app = web.Application(client_max_size=0)
    web_app["bot_client"] = bot_client
    setup_routes(web_app)
    
    try:
        await bot_client.start()
        bot_info = await bot_client.get_me()
        logger.info(f"Bot Started: @{bot_info.username}")
        
        # Test Log Channel Access
        try:
            await bot_client.get_chat(config.LOG_CHANNEL)
            logger.info(f"Log Channel Verified: {config.LOG_CHANNEL}")
        except Exception as e:
            logger.error(f"Cannot Access Log Channel: {e}")
            await bot_client.stop()
            sys.exit(1)
        
        # Start Web Server
        await start_web_server(web_app, config.PORT)
        logger.info(f"Web Server Started on Port {config.PORT}")
        logger.info(f"Base URL: {config.get_base_url()}")
        
        await idle()
        
    except KeyboardInterrupt:
        logger.info("Shutdown Signal Received")
    except Exception as e:
        logger.exception(f"Fatal Error: {e}")
    finally:
        logger.info("Shutting Down...")
        if bot_client:
            await bot_client.stop()
        logger.info("Goodbye!")

if __name__ == "__main__":
    logger.info("Using default event loop (no uvloop to avoid errors)")
    asyncio.run(main())  # This fixes the event loop issue!

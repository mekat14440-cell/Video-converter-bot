import logging
import logging.config
import sys
from pyrogram import Client, idle
from aiohttp import web
import config
from server.stream_routes import routes  # আমরা setup_routes এর বদলে routes ইম্পোর্ট করছি

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
# MAIN BOT CLASS
# =============================================================================

class Bot(Client):
    def __init__(self):
        super().__init__(
            name="StreamBot",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            bot_token=config.BOT_TOKEN,
            plugins=dict(root="plugins"),
            workers=50,
            sleep_threshold=10
        )

    async def start(self):
        # ১. টেলিগ্রাম বট স্টার্ট করা
        await super().start()
        
        # নিজের তথ্য নেওয়া
        me = await self.get_me()
        self.username = me.username
        
        # Log Channel সেট করা (Stream Routes এর জন্য এটি জরুরি)
        self.upstream_log_chat = config.LOG_CHANNEL
        
        logger.info(f"Bot Started as @{me.username}")

        # ২. ওয়েব সার্ভার (Aiohttp) স্টার্ট করা
        app = web.Application()
        app.add_routes(routes)  # 🔥 এই লাইনটিই আসল ফিক্স
        
        runner = web.AppRunner(app)
        await runner.setup()
        
        # Render পোর্ট হ্যান্ডেলিং (ডিফল্ট 8080)
        bind_address = "0.0.0.0"
        PORT = config.PORT 
        
        site = web.TCPSite(runner, bind_address, PORT)
        await site.start()
        
        logger.info(f"Web Server Running on Port {PORT}")
        
        # বট যাতে বন্ধ না হয়
        await idle()

    async def stop(self, *args):
        await super().stop()
        logger.info("Bot Stopped")

# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    # uvloop ইন্সটল করা (Linux/Render এর স্পিড বাড়ানোর জন্য)
    try:
        import uvloop
        uvloop.install()
        logger.info("Using uvloop for better performance")
    except ImportError:
        pass

    # বট রান করা
    Bot().run()
    

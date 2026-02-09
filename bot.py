import logging
import logging.config
import sys
from pyrogram import Client, idle
from aiohttp import web
import config
from server.stream_routes import routes 

# লগিং সেটআপ
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

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
        await super().start()
        
        me = await self.get_me()
        self.username = me.username
        self.upstream_log_chat = config.LOG_CHANNEL
        
        logger.info(f"Bot Started as @{me.username}")

        # ওয়েব সার্ভার সেটআপ
        app = web.Application()
        
        # 🔥 ফিক্স: ক্লায়েন্টকে অ্যাপের ভেতরে ঢুকিয়ে দিচ্ছি
        # যাতে stream_routes ফাইল এখান থেকে ক্লায়েন্ট ব্যবহার করতে পারে
        app["bot_client"] = self 
        
        app.add_routes(routes)
        
        runner = web.AppRunner(app)
        await runner.setup()
        
        bind_address = "0.0.0.0"
        PORT = config.PORT 
        
        site = web.TCPSite(runner, bind_address, PORT)
        await site.start()
        
        logger.info(f"Web Server Running on Port {PORT}")
        
        await idle()

    async def stop(self, *args):
        await super().stop()
        logger.info("Bot Stopped")

if __name__ == "__main__":
    try:
        import uvloop
        uvloop.install()
    except ImportError:
        pass

    Bot().run()
    

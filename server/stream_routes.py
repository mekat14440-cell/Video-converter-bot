import time
import logging
from aiohttp import web
from pyrogram.types import Message
from pyrogram import Client

routes = web.RouteTableDef()

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.json_response({"status": "running", "maintainer": "StreamFlix"})

@routes.get("/watch/{message_id}", allow_head=True)
async def stream_handler(request):
    try:
        # মেসেজ আইডি ইন্টিজার হতে হবে
        message_id = int(request.match_info['message_id'])
    except ValueError:
        return web.Response(status=400, text="Invalid Message ID (Must be a number)")

    # বট ক্লায়েন্ট এবং চ্যানেল আইডি চেক করা
    client = request.app.get("bot_client")
    if not client:
        return web.Response(status=500, text="Error: Bot Client Not Initialized in App")
    
    log_channel = client.upstream_log_chat
    if not log_channel:
        return web.Response(status=500, text="Error: LOG_CHANNEL ID is missing in Config")

    # সরাসরি এরর দেখার জন্য আমরা এখানে Try-Catch ব্যবহার করছি
    try:
        msg = await client.get_messages(chat_id=log_channel, message_ids=message_id)
        
        # যদি মেসেজ এম্পটি হয় (মানে ডিলেট হয়ে গেছে বা নেই)
        if not msg or msg.empty:
            return web.Response(status=404, text=f"Error: Message ID {message_id} not found in Channel {log_channel}. (File deleted?)")
            
        # ভিডিও বা ফাইল আছে কিনা চেক
        media = msg.video or msg.document
        if not media:
             return web.Response(status=404, text=f"Error: Message ID {message_id} exists but has NO VIDEO file.")

        # সব ঠিক থাকলে ভিডিও স্ট্রিম করা
        file_id = media.file_id
        file_size = media.file_size
        file_name = media.file_name or "video.mp4"
        
        # ExoPlayer এর জন্য MP4 হেডার
        headers = {
            'Content-Type': 'video/mp4',
            'Content-Length': str(file_size),
            'Accept-Ranges': 'bytes',
            'Content-Disposition': f'inline; filename="{file_name}"'
        }
        
        return web.Response(
            status=200,
            headers=headers,
            body=client.stream_media(file_id)
        )

    except Exception as e:
        # 🔥 এই লাইনটিই আপনাকে আসল সমস্যা বলে দেবে
        error_text = f"CRITICAL ERROR:\n{str(e)}\n\nCheck:\n1. Is Bot Admin?\n2. Is Channel ID Correct?\n3. Did you restart the bot?"
        return web.Response(status=500, text=error_text)

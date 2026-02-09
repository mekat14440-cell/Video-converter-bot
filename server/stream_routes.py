import math
import logging
import secrets
import mimetypes
import time
from aiohttp import web
from utils.streamer import MediaStreamer
from pyrogram.types import Message

# আমরা এখানে Bot ইম্পোর্ট করব না, ফাংশনের ভেতরে করব (Circular Import ফিক্স)

routes = web.RouteTableDef()

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.json_response({
        "status": "running",
        "maintainer": "StreamFlix",
        "uptime": "online"
    })

@routes.get("/health", allow_head=True)
async def health_handler(request):
    return web.Response(status=200, text="OK")

@routes.get("/watch/{message_id}", allow_head=True)
async def stream_handler(request):
    try:
        message_id = int(request.match_info['message_id'])
        return await media_streamer(request, message_id)
    except ValueError:
        return web.Response(status=400, text="Invalid Message ID")

async def media_streamer(request, message_id: int):
    # 🔥 CRITICAL FIX: Bot এখানে ইম্পোর্ট করা হচ্ছে যাতে ক্র্যাশ না করে
    from bot import Bot
    
    range_header = request.headers.get('Range', None)
    
    try:
        msg: Message = await Bot.get_messages(
            chat_id=Bot.upstream_log_chat, 
            message_ids=message_id
        )
    except Exception as e:
        logging.error(f"Error fetching message {message_id}: {e}")
        return web.Response(status=404, text="File Not Found")

    if not msg:
        return web.Response(status=404, text="Message Not Found")
        
    # ভিডিও বা ডকুমেন্ট হ্যান্ডেলিং
    if msg.video:
        file_id = msg.video.file_id
        file_size = msg.video.file_size
        file_name = msg.video.file_name if msg.video.file_name else "video.mp4"
        mime_type = msg.video.mime_type if msg.video.mime_type else "video/mp4"
    elif msg.document:
        file_id = msg.document.file_id
        file_size = msg.document.file_size
        file_name = msg.document.file_name
        mime_type = msg.document.mime_type
    else:
        return web.Response(status=404, text="No Media Found")

    # 🔥 MAGIC FIX: MKV কে MP4 হিসেবে চালানো
    if "x-matroska" in mime_type or "mkv" in file_name.lower():
        mime_type = "video/mp4"

    # রেঞ্জ ক্যালকুলেশন
    from_bytes, until_bytes = 0, file_size - 1
    if range_header:
        try:
            from_bytes, until_bytes = range_header.replace('bytes=', '').split('-')
            from_bytes = int(from_bytes)
            until_bytes = int(until_bytes) if until_bytes else file_size - 1
        except ValueError:
            pass

    if from_bytes >= file_size:
        return web.Response(
            status=416, 
            headers={'Content-Range': f'bytes */{file_size}'}
        )

    chunk_size = 1024 * 1024
    until_bytes = min(until_bytes, file_size - 1)
    length = until_bytes - from_bytes + 1
    
    headers = {
        'Content-Type': mime_type,
        'Content-Range': f'bytes {from_bytes}-{until_bytes}/{file_size}',
        'Content-Length': str(length),
        'Accept-Ranges': 'bytes',
        'Content-Disposition': f'inline; filename="{file_name}"',
        'Access-Control-Allow-Origin': '*',
    }

    return web.Response(
        status=206 if range_header else 200,
        headers=headers,
        body=Bot.stream_media(file_id, offset=from_bytes, length=length)
    )
    

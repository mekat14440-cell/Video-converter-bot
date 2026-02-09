import math
import logging
import secrets
import mimetypes
import time
from aiohttp import web
from bot import Bot
from utils.streamer import MediaStreamer
from pyrogram.types import Message

routes = web.RouteTableDef()

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    """
    Root route to check if bot is running.
    """
    return web.json_response({
        "status": "running",
        "maintainer": "StreamFlix",
        "uptime": "online"
    })

@routes.get("/health", allow_head=True)
async def health_handler(request):
    """
    Health check for Render to keep the bot alive.
    """
    return web.Response(status=200, text="OK")

@routes.get("/watch/{message_id}", allow_head=True)
async def stream_handler(request):
    """
    Main streaming endpoint: /watch/123
    Handles Range Requests for video seeking.
    """
    try:
        message_id = int(request.match_info['message_id'])
        return await media_streamer(request, message_id)
    except ValueError:
        return web.Response(status=400, text="Invalid Message ID")

async def media_streamer(request, message_id: int):
    range_header = request.headers.get('Range', None)
    
    # 1. Fetch Message from Telegram Channel (Log Channel)
    try:
        msg: Message = await Bot.get_messages(
            chat_id=Bot.upstream_log_chat, 
            message_ids=message_id
        )
    except Exception as e:
        logging.error(f"Error fetching message {message_id}: {e}")
        return web.Response(status=404, text="File Not Found or Bot was kicked from channel.")

    if not msg or not msg.video:
        # Also support Documents that are videos
        if msg.document and "video" in msg.document.mime_type:
            file_id = msg.document.file_id
            file_size = msg.document.file_size
            file_name = msg.document.file_name
            mime_type = msg.document.mime_type
        else:
            return web.Response(status=404, text="No Video Content Found")
    else:
        file_id = msg.video.file_id
        file_size = msg.video.file_size
        file_name = msg.video.file_name if msg.video.file_name else "video.mp4"
        mime_type = msg.video.mime_type if msg.video.mime_type else "video/mp4"

    # 🔥 MAGIC FIX: Force Content-Type to MP4 for MKV files
    # Android VideoView plays MKV better if it thinks it's MP4 or Generic Video
    if "x-matroska" in mime_type or "mkv" in file_name.lower():
        mime_type = "video/mp4"

    # 2. Calculate Byte Ranges (Crucial for seeking/buffering)
    from_bytes, until_bytes = 0, file_size - 1
    if range_header:
        try:
            from_bytes, until_bytes = range_header.replace('bytes=', '').split('-')
            from_bytes = int(from_bytes)
            until_bytes = int(until_bytes) if until_bytes else file_size - 1
        except ValueError:
            pass # Invalid range, fallback to full file

    # Ensure range is valid
    if from_bytes >= file_size:
        return web.Response(
            status=416, 
            body="416: Requested Range Not Satisfiable",
            headers={'Content-Range': f'bytes */{file_size}'}
        )

    chunk_size = 1024 * 1024 # 1MB Chunk default
    until_bytes = min(until_bytes, file_size - 1)
    
    # Calculate content length for this request
    length = until_bytes - from_bytes + 1
    
    # 3. Setup Response Headers
    headers = {
        'Content-Type': mime_type,
        'Content-Range': f'bytes {from_bytes}-{until_bytes}/{file_size}',
        'Content-Length': str(length),
        'Accept-Ranges': 'bytes',
        'Content-Disposition': f'inline; filename="{file_name}"',
        'Access-Control-Allow-Origin': '*', # Allow all apps
    }

    # 4. Return Stream Response
    return web.Response(
        status=206 if range_header else 200,
        headers=headers,
        body=Bot.stream_media(file_id, offset=from_bytes, length=length)
    )
    

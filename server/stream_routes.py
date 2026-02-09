import math
import logging
import mimetypes
from aiohttp import web
from pyrogram.types import Message
from pyrogram import Client
from pyrogram.errors import ChannelInvalid, ChannelPrivate, PeerIdInvalid

routes = web.RouteTableDef()

@routes.get("/", allow_head=True)
async def root_route_handler(request):
    return web.json_response({"status": "running", "maintainer": "StreamFlix"})

@routes.get("/watch/{message_id}", allow_head=True)
async def stream_handler(request):
    try:
        message_id = int(request.match_info['message_id'])
        return await media_streamer(request, message_id)
    except ValueError:
        return web.Response(status=400, text="Invalid Message ID")

async def media_streamer(request, message_id: int):
    client: Client = request.app["bot_client"]
    log_channel = client.upstream_log_chat

    # 1. ফাইল খোঁজা শুরু
    try:
        msg: Message = await client.get_messages(chat_id=log_channel, message_ids=message_id)
    except PeerIdInvalid:
        return web.Response(status=500, text=f"Error: Bot cannot find Channel ID ({log_channel}). Make sure ID starts with -100")
    except ChannelInvalid:
        return web.Response(status=500, text="Error: Channel Invalid or Bot is not Admin.")
    except Exception as e:
        return web.Response(status=500, text=f"Unknown Error: {str(e)}")

    # 2. মেসেজ চেক করা
    if not msg or msg.empty:
        return web.Response(status=404, text="Error: Message not found (File deleted?)")

    # 3. ভিডিও বা ডকুমেন্ট আছে কিনা দেখা
    tag = msg.video or msg.document
    if not tag:
        return web.Response(status=404, text="Error: No video found in this message")

    file_id = tag.file_id
    file_size = tag.file_size
    file_name = tag.file_name or "video.mp4"
    
    # 4. রেঞ্জ রিকোয়েস্ট হ্যান্ডেল করা (ExoPlayer এর জন্য জরুরি)
    range_header = request.headers.get('Range', None)
    from_bytes, until_bytes = 0, file_size - 1
    
    if range_header:
        try:
            from_bytes, until_bytes = range_header.replace('bytes=', '').split('-')
            from_bytes = int(from_bytes)
            until_bytes = int(until_bytes) if until_bytes else file_size - 1
        except ValueError:
            pass

    length = until_bytes - from_bytes + 1
    
    # 5. রেসপন্স হেডার (MP4 হিসেবে পাঠানো)
    headers = {
        'Content-Type': 'video/mp4',
        'Content-Range': f'bytes {from_bytes}-{until_bytes}/{file_size}',
        'Content-Length': str(length),
        'Accept-Ranges': 'bytes',
        'Content-Disposition': f'inline; filename="{file_name}"',
        'Access-Control-Allow-Origin': '*'
    }

    return web.Response(
        status=206 if range_header else 200,
        headers=headers,
        body=client.stream_media(file_id, offset=from_bytes, length=length)
    )
    

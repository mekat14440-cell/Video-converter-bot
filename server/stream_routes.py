"""
Stream Routes - Aiohttp routes for file streaming.

This module handles:
- /watch/{message_id} - Stream a file for playback
- /download/{message_id}/{file_name} - Download a file
- Health check endpoint
"""

import logging
import mimetypes
from urllib.parse import quote

from aiohttp import web
from pyrogram import Client

import config
from utils.streamer import ByteStreamer, FileNotFoundError, StreamerError

logger = logging.getLogger(__name__)

# Store streamer instance globally
_streamer: ByteStreamer = None


def get_streamer(app: web.Application) -> ByteStreamer:
    """Get or create ByteStreamer instance."""
    global _streamer
    if _streamer is None:
        client: Client = app["bot_client"]
        _streamer = ByteStreamer(client)
    return _streamer


async def health_check(request: web.Request) -> web.Response:
    """
    Health check endpoint for Render.
    
    Returns:
        200 OK if service is healthy
    """
    return web.json_response({
        "status": "healthy",
        "service": "telegram-stream-bot"
    })


async def home_page(request: web.Request) -> web.Response:
    """
    Home page with basic information.
    """
    html = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Telegram Stream Bot</title>
        <style>
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                max-width: 800px;
                margin: 0 auto;
                padding: 20px;
                background: #1a1a2e;
                color: #eee;
            }
            h1 { color: #0088cc; }
            .info { background: #16213e; padding: 20px; border-radius: 10px; }
            a { color: #00adb5; }
        </style>
    </head>
    <body>
        <h1>🎬 Telegram Stream Bot</h1>
        <div class="info">
            <p>This is a file streaming service powered by Telegram.</p>
            <p>Send files to the bot to generate stream links.</p>
            <p><a href="https://t.me/YourBotUsername">Open Bot on Telegram</a></p>
        </div>
    </body>
    </html>
    """
    return web.Response(text=html, content_type="text/html")


async def stream_handler(request: web.Request) -> web.StreamResponse:
    """
    Handle streaming requests.
    
    Route: /watch/{message_id}
    
    This endpoint:
    1. Fetches file metadata from the log channel
    2. Handles Range requests for seeking
    3. Streams file chunks from Telegram to the client
    """
    try:
        message_id = int(request.match_info["message_id"])
    except (ValueError, KeyError):
        return web.Response(status=400, text="Invalid message ID")
    
    streamer = get_streamer(request.app)
    
    try:
        # Get file properties
        properties = await streamer.get_file_properties(message_id)
        
        file_id = properties["file_id"]
        file_size = properties["file_size"]
        file_name = properties["file_name"]
        mime_type = properties["mime_type"]
        
        # Ensure proper mime type for videos
        if mime_type == "application/octet-stream":
            guessed_type, _ = mimetypes.guess_type(file_name)
            if guessed_type:
                mime_type = guessed_type
            elif file_name.lower().endswith(('.mp4', '.m4v')):
                mime_type = "video/mp4"
            elif file_name.lower().endswith('.mkv'):
                mime_type = "video/x-matroska"
        
        # Parse Range header
        range_header = request.headers.get("Range")
        start, end = streamer.parse_range_header(range_header, file_size)
        
        # Calculate content length
        content_length = end - start + 1
        
        # Determine status code
        if range_header:
            status = 206  # Partial Content
        else:
            status = 200  # OK
        
        # Build response headers
        headers = {
            "Content-Type": mime_type,
            "Content-Length": str(content_length),
            "Accept-Ranges": "bytes",
            "Content-Disposition": f'inline; filename="{quote(file_name)}"',
            # CORS headers for web players
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
            "Access-Control-Allow-Headers": "Range",
            "Access-Control-Expose-Headers": "Content-Range, Content-Length, Accept-Ranges",
        }
        
        if status == 206:
            headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
        
        # Create streaming response
        response = web.StreamResponse(
            status=status,
            headers=headers
        )
        
        await response.prepare(request)
        
        # Stream the file
        logger.info(f"Streaming message {message_id}: bytes {start}-{end}/{file_size}")
        
        async for chunk in streamer.yield_file(file_id, offset=start, limit=content_length):
            await response.write(chunk)
        
        await response.write_eof()
        
        return response
        
    except FileNotFoundError as e:
        logger.warning(f"File not found: message_id={message_id}, error={e}")
        return web.Response(
            status=404,
            text="File not found. The link may have expired or the file was deleted."
        )
    except StreamerError as e:
        logger.error(f"Streaming error: message_id={message_id}, error={e}")
        return web.Response(
            status=500,
            text="An error occurred while streaming the file."
        )
    except Exception as e:
        logger.exception(f"Unexpected error: message_id={message_id}, error={e}")
        return web.Response(
            status=500,
            text="Internal server error."
        )


async def download_handler(request: web.Request) -> web.StreamResponse:
    """
    Handle download requests (forces download instead of playing).
    
    Route: /download/{message_id}/{file_name}
    """
    try:
        message_id = int(request.match_info["message_id"])
        file_name = request.match_info.get("file_name", "file")
    except (ValueError, KeyError):
        return web.Response(status=400, text="Invalid request")
    
    streamer = get_streamer(request.app)
    
    try:
        properties = await streamer.get_file_properties(message_id)
        
        file_id = properties["file_id"]
        file_size = properties["file_size"]
        original_name = properties["file_name"]
        mime_type = properties["mime_type"]
        
        # Use original name if available
        if original_name and original_name != "file":
            file_name = original_name
        
        # Parse Range header
        range_header = request.headers.get("Range")
        start, end = streamer.parse_range_header(range_header, file_size)
        content_length = end - start + 1
        
        status = 206 if range_header else 200
        
        headers = {
            "Content-Type": mime_type,
            "Content-Length": str(content_length),
            "Accept-Ranges": "bytes",
            # Force download with attachment disposition
            "Content-Disposition": f'attachment; filename="{quote(file_name)}"',
            "Access-Control-Allow-Origin": "*",
        }
        
        if status == 206:
            headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
        
        response = web.StreamResponse(status=status, headers=headers)
        await response.prepare(request)
        
        async for chunk in streamer.yield_file(file_id, offset=start, limit=content_length):
            await response.write(chunk)
        
        await response.write_eof()
        return response
        
    except FileNotFoundError:
        return web.Response(status=404, text="File not found")
    except Exception as e:
        logger.exception(f"Download error: {e}")
        return web.Response(status=500, text="Download failed")


async def options_handler(request: web.Request) -> web.Response:
    """
    Handle CORS preflight requests.
    """
    return web.Response(
        headers={
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
            "Access-Control-Allow-Headers": "Range, Content-Type",
            "Access-Control-Max-Age": "86400",
        }
    )


def setup_routes(app: web.Application):
    """
    Setup all routes for the web application.
    
    Args:
        app: The aiohttp web application
    """
    # Home page
    app.router.add_get("/", home_page)
    
    # Health check (for Render)
    app.router.add_get("/health", health_check)
    
    # Stream endpoint
    app.router.add_get("/watch/{message_id}", stream_handler)
    app.router.add_head("/watch/{message_id}", stream_handler)
    app.router.add_options("/watch/{message_id}", options_handler)
    
    # Download endpoint
    app.router.add_get("/download/{message_id}/{file_name}", download_handler)
    app.router.add_get("/download/{message_id}", download_handler)
    app.router.add_head("/download/{message_id}/{file_name}", download_handler)
    app.router.add_options("/download/{message_id}/{file_name}", options_handler)
    
    logger.info("Routes configured successfully")

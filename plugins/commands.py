"""
Command Handlers for the Telegram Stream Bot.

This module handles:
- /start command: Welcome message and usage instructions
- Incoming files: Forward to log channel and generate stream link
"""

import logging
from typing import Optional

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.enums import ParseMode, ChatType

import config

logger = logging.getLogger(__name__)

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_file_info(message: Message) -> Optional[dict]:
    """
    Extract file information from a message.
    
    Args:
        message: The Pyrogram message object
        
    Returns:
        dict with file info or None if no supported media
    """
    media = None
    media_type = None
    
    if message.video:
        media = message.video
        media_type = "video"
    elif message.document:
        media = message.document
        media_type = "document"
    elif message.audio:
        media = message.audio
        media_type = "audio"
    elif message.voice:
        media = message.voice
        media_type = "voice"
    elif message.video_note:
        media = message.video_note
        media_type = "video_note"
    elif message.animation:
        media = message.animation
        media_type = "animation"
    elif message.photo:
        media = message.photo[-1]  # Get highest resolution
        media_type = "photo"
    
    if not media:
        return None
    
    return {
        "media": media,
        "type": media_type,
        "file_id": media.file_id,
        "file_unique_id": media.file_unique_id,
        "file_size": getattr(media, "file_size", 0),
        "file_name": getattr(media, "file_name", f"file.{media_type}"),
        "mime_type": getattr(media, "mime_type", "application/octet-stream"),
        "duration": getattr(media, "duration", None),
        "width": getattr(media, "width", None),
        "height": getattr(media, "height", None),
    }


def format_size(size_bytes: int) -> str:
    """Convert bytes to human readable format."""
    if size_bytes == 0:
        return "0 B"
    
    units = ["B", "KB", "MB", "GB", "TB"]
    unit_index = 0
    size = float(size_bytes)
    
    while size >= 1024 and unit_index < len(units) - 1:
        size /= 1024
        unit_index += 1
    
    return f"{size:.2f} {units[unit_index]}"


def format_duration(seconds: Optional[int]) -> str:
    """Convert seconds to HH:MM:SS format."""
    if not seconds:
        return "N/A"
    
    hours, remainder = divmod(seconds, 3600)
    minutes, secs = divmod(remainder, 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def generate_stream_link(message_id: int) -> str:
    """
    Generate the stream URL for a file.
    
    Args:
        message_id: The message ID in the log channel
        
    Returns:
        The complete stream URL
    """
    base_url = config.get_base_url()
    return f"{base_url}/watch/{message_id}"


def generate_download_link(message_id: int, file_name: str) -> str:
    """
    Generate the download URL for a file.
    
    Args:
        message_id: The message ID in the log channel
        file_name: The original file name
        
    Returns:
        The complete download URL
    """
    base_url = config.get_base_url()
    # URL encode the filename for safety
    safe_name = file_name.replace(" ", "_")
    return f"{base_url}/download/{message_id}/{safe_name}"


# =============================================================================
# COMMAND HANDLERS
# =============================================================================

@Client.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    """
    Handle /start command - Send welcome message with instructions.
    """
    user = message.from_user
    
    welcome_text = f"""
**👋 Welcome, {user.mention}!**

I'm a **File Streaming Bot** that generates direct stream links for your files.

**📝 How to use:**
1️⃣ Send me any file (video, audio, document, etc.)
2️⃣ I'll generate a **direct stream link** for you
3️⃣ Use the link to stream/download the file anywhere!

**✨ Features:**
• **No Download Needed** - Stream directly
• **Fast CDN** - Powered by Telegram servers
• **ExoPlayer Compatible** - Works with Android apps
• **Range Requests** - Supports seeking in videos
• **No Expiry** - Links work as long as the file exists

**📌 Supported File Types:**
• 🎬 Videos (MP4, MKV, AVI, etc.)
• 🎵 Audio (MP3, FLAC, etc.)
• 📄 Documents (PDF, ZIP, etc.)
• 🖼️ Photos

**⚡ Just send a file to get started!**
"""
    
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📢 Updates Channel", url="https://t.me/YourChannel"),
            InlineKeyboardButton("💬 Support", url="https://t.me/YourSupport")
        ]
    ])
    
    await message.reply_text(
        welcome_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )
    
    logger.info(f"User {user.id} ({user.first_name}) started the bot")


@Client.on_message(filters.command("help") & filters.private)
async def help_command(client: Client, message: Message):
    """
    Handle /help command.
    """
    help_text = """
**📖 Help Guide**

**Commands:**
• `/start` - Start the bot
• `/help` - Show this help message
• `/about` - About the bot

**How Streaming Works:**
When you send a file, I forward it to a secure channel and generate a unique link. When someone opens the link, the file streams directly from Telegram servers - no storage needed!

**Tips:**
• For best video playback, use MP4 format
• Large files may take a moment to start streaming
• Links are permanent unless you delete the source file

**Having Issues?**
Make sure you're using a player that supports HTTP streaming (VLC, MX Player, ExoPlayer).
"""
    
    await message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)


@Client.on_message(filters.command("about") & filters.private)
async def about_command(client: Client, message: Message):
    """
    Handle /about command.
    """
    about_text = """
**ℹ️ About This Bot**

**Version:** 1.0.0
**Framework:** Pyrogram + Aiohttp
**Platform:** Render

This bot is designed to stream Telegram files without downloading them to disk. It acts as a proxy between Telegram servers and your media player.

**Technical Details:**
• Uses Range Request support for seeking
• Streams in 1MB chunks
• Supports concurrent connections
• Zero disk storage required
"""
    
    await message.reply_text(about_text, parse_mode=ParseMode.MARKDOWN)


# =============================================================================
# FILE HANDLERS
# =============================================================================

@Client.on_message(
    filters.private & 
    (filters.video | filters.document | filters.audio | 
     filters.voice | filters.video_note | filters.animation | filters.photo)
)
async def handle_file(client: Client, message: Message):
    """
    Handle incoming files - Forward to log channel and generate stream link.
    """
    user = message.from_user
    
    # Extract file information
    file_info = get_file_info(message)
    
    if not file_info:
        await message.reply_text("❌ Could not process this file type.")
        return
    
    # Send processing message
    processing_msg = await message.reply_text("⏳ Processing your file...")
    
    try:
        # Forward the file to the log channel
        forwarded = await message.forward(config.LOG_CHANNEL)
        
        if not forwarded:
            await processing_msg.edit_text("❌ Failed to process file. Please try again.")
            return
        
        # Generate links using the log channel message ID
        message_id = forwarded.id
        stream_link = generate_stream_link(message_id)
        download_link = generate_download_link(message_id, file_info["file_name"])
        
        # Build response message
        response_text = f"""
**✅ Your Stream Link is Ready!**

**📁 File Information:**
• **Name:** `{file_info['file_name']}`
• **Size:** {format_size(file_info['file_size'])}
• **Type:** {file_info['mime_type']}
"""
        
        # Add duration for videos/audio
        if file_info["duration"]:
            response_text += f"• **Duration:** {format_duration(file_info['duration'])}\n"
        
        # Add resolution for videos/photos
        if file_info["width"] and file_info["height"]:
            response_text += f"• **Resolution:** {file_info['width']}x{file_info['height']}\n"
        
        response_text += f"""
**🔗 Stream Link:**
`{stream_link}`

**📥 Download Link:**
`{download_link}`

**💡 Tip:** Copy the stream link and paste it in VLC, MX Player, or any media player that supports HTTP streaming.
"""
        
        # Create keyboard with quick action buttons
        keyboard = InlineKeyboardMarkup([
            [
                InlineKeyboardButton("🎬 Open Stream", url=stream_link),
            ],
            [
                InlineKeyboardButton("📥 Download", url=download_link),
            ]
        ])
        
        await processing_msg.edit_text(
            response_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard,
            disable_web_page_preview=True
        )
        
        logger.info(
            f"Generated link for user {user.id}: "
            f"file={file_info['file_name']}, "
            f"size={format_size(file_info['file_size'])}, "
            f"msg_id={message_id}"
        )
        
    except Exception as e:
        logger.exception(f"Error processing file from user {user.id}: {e}")
        await processing_msg.edit_text(
            f"❌ An error occurred while processing your file.\n\n"
            f"Error: `{str(e)}`\n\n"
            f"Please try again or contact support."
        )


# =============================================================================
# ERROR HANDLER
# =============================================================================

@Client.on_message(filters.private & ~filters.command(["start", "help", "about"]) & filters.text)
async def handle_text(client: Client, message: Message):
    """
    Handle random text messages.
    """
    await message.reply_text(
        "📁 Please send me a **file** (video, audio, or document) to generate a stream link.\n\n"
        "Use /help for more information.",
        parse_mode=ParseMode.MARKDOWN
    )

"""
Command Handlers for the Telegram Stream Bot.
Updated to fix BUTTON_URL_INVALID error.
"""

import logging
from typing import Optional
from urllib.parse import quote  # URL এনকোডিং এর জন্য এটি যুক্ত করা হয়েছে

from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardButton, InlineKeyboardMarkup
from pyrogram.enums import ParseMode

import config

logger = logging.getLogger(__name__)

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_file_info(message: Message) -> Optional[dict]:
    """Extract file information from a message."""
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
        "file_name": getattr(media, "file_name", f"file_{media.file_unique_id}.{media_type}"), # Fallback name fixed
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


def clean_base_url(url: str) -> str:
    """Ensure the base URL is formatted correctly."""
    url = url.strip().rstrip("/")
    # যদি ভুলে ডাবল https:// হয়ে যায়, সেটা ঠিক করা
    if url.startswith("https://https://"):
        url = url.replace("https://https://", "https://")
    elif url.startswith("http://http://"):
        url = url.replace("http://http://", "http://")
    return url


def generate_stream_link(message_id: int) -> str:
    """Generate the stream URL for a file."""
    base_url = clean_base_url(config.get_base_url())
    return f"{base_url}/watch/{message_id}"


def generate_download_link(message_id: int, file_name: str) -> str:
    """Generate the download URL for a file."""
    base_url = clean_base_url(config.get_base_url())
    
    # Fix: Use quote to handle spaces and special characters safely
    # আগের কোডে শুধু replace(" ", "_") ছিল যা যথেষ্ট নয়
    safe_name = quote(file_name) 
    
    return f"{base_url}/download/{message_id}/{safe_name}"


# =============================================================================
# COMMAND HANDLERS
# =============================================================================

@Client.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    """Handle /start command."""
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

**⚡ Just send a file to get started!**
"""
    
    # Update these URLs to your actual channel/support if needed
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton("📢 Updates Channel", url="https://t.me/telegram"),
            InlineKeyboardButton("💬 Support", url="https://t.me/telegram")
        ]
    ])
    
    await message.reply_text(
        welcome_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard,
        disable_web_page_preview=True
    )


@Client.on_message(filters.command("help") & filters.private)
async def help_command(client: Client, message: Message):
    """Handle /help command."""
    help_text = """
**📖 Help Guide**

**Commands:**
• `/start` - Start the bot
• `/help` - Show this help message
• `/about` - About the bot

**Tips:**
• For best video playback, use MP4/MKV format
• Links are permanent unless you delete the source file
"""
    await message.reply_text(help_text, parse_mode=ParseMode.MARKDOWN)


@Client.on_message(filters.command("about") & filters.private)
async def about_command(client: Client, message: Message):
    """Handle /about command."""
    about_text = """
**ℹ️ About This Bot**
**Version:** 1.0.1 (Fix)
**Framework:** Pyrogram + Aiohttp
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
    """Handle incoming files."""
    user = message.from_user
    
    file_info = get_file_info(message)
    if not file_info:
        await message.reply_text("❌ Could not process this file type.")
        return
    
    processing_msg = await message.reply_text("⏳ Processing your file...")
    
    try:
        # Forward to log channel
        try:
            forwarded = await message.forward(config.LOG_CHANNEL)
        except Exception as e:
            await processing_msg.edit_text(f"❌ Error: Make sure Bot is Admin in Log Channel.\n{e}")
            return

        message_id = forwarded.id
        stream_link = generate_stream_link(message_id)
        download_link = generate_download_link(message_id, file_info["file_name"])
        
        response_text = f"""
**✅ Your Stream Link is Ready!**

**📁 File Name:** `{file_info['file_name']}`
**💾 Size:** {format_size(file_info['file_size'])}

**🔗 Stream Link:**
`{stream_link}`

**📥 Download Link:**
`{download_link}`
"""
        
        # Keyboard creation
        buttons = [
            [InlineKeyboardButton("🎬 Open Stream", url=stream_link)],
            [InlineKeyboardButton("📥 Download", url=download_link)]
        ]
        
        await processing_msg.edit_text(
            response_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(buttons),
            disable_web_page_preview=True
        )
        
        logger.info(f"Link generated for user {user.id} | MsgID: {message_id}")
        
    except Exception as e:
        logger.exception(f"Error processing file: {e}")
        await processing_msg.edit_text(f"❌ An error occurred: {str(e)}")


@Client.on_message(filters.private & ~filters.command(["start", "help", "about"]) & filters.text)
async def handle_text(client: Client, message: Message):
    """Handle random text messages."""
    await message.reply_text(
        "📁 Please send me a **file** to generate a stream link.",
        parse_mode=ParseMode.MARKDOWN
)
    

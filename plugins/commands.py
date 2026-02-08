"""
Fixed version - No Inline Buttons = No BUTTON_URL_INVALID Error!
"""

import logging
from typing import Optional
from pyrogram import Client, filters
from pyrogram.types import Message
from pyrogram.enums import ParseMode

import config

logger = logging.getLogger(__name__)

# =============================================================================
# Helper Functions (Same as before)
# =============================================================================
def get_file_info(message: Message) -> Optional[dict]:
    media = None
    if message.video:
        media = message.video
    elif message.document:
        media = message.document
    elif message.audio:
        media = message.audio
    elif message.voice:
        media = message.voice
    elif message.video_note:
        media = message.video_note
    elif message.animation:
        media = message.animation
    elif message.photo:
        media = message.photo[-1]
    
    if not media:
        return None
    
    return {
        "media": media,
        "file_name": getattr(media, "file_name", "Unknown File"),
        "file_size": getattr(media, "file_size", 0),
        "mime_type": getattr(media, "mime_type", "video/mp4"),
        "duration": getattr(media, "duration", None),
        "width": getattr(media, "width", None),
        "height": getattr(media, "height", None),
    }

def format_size(size_bytes: int) -> str:
    if not size_bytes: return "Unknown"
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024: return f"{size_bytes:.2f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.2f} TB"

def format_duration(seconds: Optional[int]) -> str:
    if not seconds: return "N/A"
    hours, rem = divmod(seconds, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}" if hours else f"{minutes:02d}:{seconds:02d}"

def generate_stream_link(message_id: int) -> str:
    return f"{config.get_base_url()}/watch/{message_id}"

# =============================================================================
# Start Command
# =============================================================================
@Client.on_message(filters.command("start") & filters.private)
async def start_command(client: Client, message: Message):
    await message.reply_text(
        "Bot Active Hai!\n\n"
        "Mujhe koi bhi **video/file** forward karo – main turant **direct streaming link** dunga!\n\n"
        "MP4, MKV, AVI – sab chalega!",
        parse_mode=ParseMode.MARKDOWN
    )

# =============================================================================
# Main File Handler (Fixed – No Buttons!)
# =============================================================================
@Client.on_message(
    filters.private & 
    (filters.video | filters.document | filters.audio | filters.animation)
)
async def handle_file(client: Client, message: Message):
    processing = await message.reply_text("Processing...")

    try:
        file_info = get_file_info(message)
        if not file_info:
            return await processing.edit_text("Yeh file type support nahi karta!")

        # Forward to log channel
        forwarded = await message.forward(config.LOG_CHANNEL)
        msg_id = forwarded.id

        stream_link = generate_stream_link(msg_id)

        caption = f"""
**Streaming Link Ready!**

**File:** `{file_info['file_name']}`
**Size:** {format_size(file_info['file_size'])}
**Duration:** {format_duration(file_info['duration'])}

**Direct Stream Link:**
`{stream_link}`

Copy karke MX Player, VLC ya kisi bhi player mein paste kar do – turant play hoga!
        """

        await processing.edit_text(
            caption.strip(),
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )

    except Exception as e:
        logger.error(f"Error: {e}")
        await processing.edit_text(f"Error aaya bhai: `{str(e)[:100]}`")

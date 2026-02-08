import os
import time
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from config import API_ID, API_HASH, BOT_TOKEN
from helper import (
    progress_for_pyrogram,
    download_file_from_url,
    extract_thumbnail,
    convert_video,
    cleanup_files,
    is_valid_url
)

# Pyrogram ক্লায়েন্ট
app = Client(
    "video_converter_bot",
    api_id=API_ID,
    api_hash=API_HASH,
    bot_token=BOT_TOKEN
)

# স্টার্ট কমান্ড
@app.on_message(filters.command("start"))
async def start_command(client: Client, message: Message):
    welcome_text = (
        "👋 **স্বাগতম! আমি ভিডিও কনভার্টর বট**\n\n"
        "✅ **আমি যা করতে পারি:**\n"
        "├ 📁 **ফরওয়ার্ডেড ফাইল**: যেকোনো ভিডিও ফাইল পাঠান\n"
        "├ 🔗 **ডাইরেক্ট লিংক**: ভিডিওর ডাউনলোড লিংক পাঠান\n"
        "└ 🎬 **আউটপুট**: Android সাপোর্টেড MP4 (H.264 + AAC)\n\n"
        "⚡ **ফাস্ট কনভারশন**: Ultrafast প্রিসেট ব্যবহার করা হয়\n"
        "📱 **পারফেক্ট**: আপনার অ্যাপের VideoView এর জন্য"
    )
    
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("👨‍💻 ডেভেলপার", url="https://t.me/your_username")]
    ])
    
    await message.reply_text(welcome_text, reply_markup=keyboard)

# মেইন মেসেজ হ্যান্ডলার
@app.on_message(filters.private & (filters.document | filters.video | filters.text))
async def handle_media(client: Client, message: Message):
    # প্রসেসিং মেসেজ
    processing_msg = await message.reply_text("🔄 প্রসেসিং শুরু হচ্ছে...", quote=True)
    
    input_path = None
    output_path = None
    thumbnail_path = None
    
    try:
        # চেক করবে ইনপুট কী ধরনের
        if message.document or message.video:
            # ========== টেলিগ্রাম ফাইল হ্যান্ডলিং ==========
            file = message.document or message.video
            file_name = file.file_name or f"video_{int(time.time())}.mp4"
            
            # ফাইল এক্সটেনশন চেক
            if not any(ext in file_name.lower() for ext in ['.mkv', '.mp4', '.avi', '.webm', '.hevc', '.mov']):
                await processing_msg.edit_text("❌ এই ফাইল টাইপ সাপোর্ট করা হয় না। শুধু ভিডিও ফাইল পাঠান।")
                return
            
            # টেম্পরারি ডিরেক্টরি
            temp_dir = f"temp_{message.from_user.id}"
            os.makedirs(temp_dir, exist_ok=True)
            
            input_path = os.path.join(temp_dir, file_name)
            base_name = os.path.splitext(file_name)[0]
            output_path = os.path.join(temp_dir, f"{base_name}_converted.mp4")
            thumbnail_path = os.path.join(temp_dir, "thumbnail.jpg")
            
            # ডাউনলোড ফাইল
            await processing_msg.edit_text("📥 ডাউনলোড হচ্ছে...")
            start_time = time.time()
            
            try:
                await client.download_media(
                    message,
                    file_name=input_path,
                    progress=progress_for_pyrogram,
                    progress_args=("ডাউনলোড হচ্ছে...", processing_msg, start_time)
                )
            except Exception as e:
                raise Exception(f"ডাউনলোড ব্যর্থ: {str(e)}")
            
            # থাম্বনেইল চেক
            if file.thumbs:
                try:
                    await client.download_media(
                        file.thumbs[0].file_id,
                        file_name=thumbnail_path
                    )
                except:
                    pass
            
        elif message.text and is_valid_url(message.text):
            # ========== URL হ্যান্ডলিং ==========
            url = message.text.strip()
            temp_dir = f"temp_{message.from_user.id}"
            os.makedirs(temp_dir, exist_ok=True)
            
            # ফাইল নেম জেনারেট
            file_name = f"video_{int(time.time())}.mp4"
            input_path = os.path.join(temp_dir, file_name)
            base_name = os.path.splitext(file_name)[0]
            output_path = os.path.join(temp_dir, f"{base_name}_converted.mp4")
            thumbnail_path = os.path.join(temp_dir, "thumbnail.jpg")
            
            # ডাউনলোড ফ্রম URL
            await processing_msg.edit_text("🔗 URL থেকে ডাউনলোড হচ্ছে...")
            
            success = download_file_from_url(url, input_path, processing_msg)
            if not success:
                raise Exception("URL থেকে ডাউনলোড ব্যর্থ হয়েছে।")
            
        else:
            await processing_msg.edit_text(
                "❌ **ভুল ইনপুট!**\n\n"
                "✅ **সঠিক ইনপুট:**\n"
                "• একটি ভিডিও ফাইল ফরওয়ার্ড করুন\n"
                "• অথবা ডাইরেক্ট ডাউনলোড লিংক পাঠান"
            )
            return
        
        # ========== কনভারশন ==========
        if not os.path.exists(input_path):
            raise Exception("ইনপুট ফাইল পাওয়া যায়নি!")
        
        await processing_msg.edit_text("🎬 কনভার্ট হচ্ছে... এটি কিছু সময় নিতে পারে")
        
        success = convert_video(input_path, output_path, processing_msg)
        if not success:
            raise Exception("ভিডিও কনভারশন ব্যর্থ হয়েছে।")
        
        # থাম্বনেইল না থাকলে এক্সট্র্যাক্ট করবে
        if not os.path.exists(thumbnail_path):
            extract_thumbnail(output_path, thumbnail_path)
        
        # ========== আপলোড ==========
        await processing_msg.edit_text("📤 আপলোড হচ্ছে...")
        start_time = time.time()
        
        # আপলোড অপশন
        upload_kwargs = {
            "thumb": thumbnail_path if os.path.exists(thumbnail_path) else None,
            "caption": f"✅ কনভার্টেড: {os.path.basename(output_path)}\n🤖 @YourBotUsername",
            "progress": progress_for_pyrogram,
            "progress_args": ("আপলোড হচ্ছে...", processing_msg, start_time)
        }
        
        # ভিডিও আকারে আপলোড
        await client.send_video(
            chat_id=message.chat.id,
            video=output_path,
            supports_streaming=True,  # স্ট্রিমিং সাপোর্ট
            **upload_kwargs
        )
        
        # সাকসেস মেসেজ
        await processing_msg.edit_text("✅ **সম্পূর্ণ হয়েছে!**")
        
    except Exception as e:
        error_msg = f"❌ **এড়র:** {str(e)}\n\n💡 টিপ: ফাইল সাইজ বড় হলে সময় বেশি লাগতে পারে।"
        await processing_msg.edit_text(error_msg)
    
    finally:
        # ========== ক্লিনআপ ==========
        await processing_msg.edit_text("🧹 টেম্পরারি ফাইল ডিলিট হচ্ছে...")
        cleanup_files(input_path, output_path, thumbnail_path)
        
        # খালি ডিরেক্টরি ডিলিট
        try:
            if 'temp_dir' in locals():
                os.rmdir(temp_dir)
        except:
            pass
        
        # ফাইনাল মেসেজ
        await processing_msg.edit_text("✅ **প্রসেস সম্পূর্ণ!**")

# রান বট
if __name__ == "__main__":
    print("🚀 বট স্টার্ট হচ্ছে...")
    app.run()

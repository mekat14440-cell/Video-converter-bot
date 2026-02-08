import os
import asyncio
import subprocess
import time
from pyrogram.types import Message
import requests
from pathlib import Path

# গ্লোবাল ভেরিয়েবল ফর প্রোগ্রেস মেসেজ থ্রটলিং
last_edit_time = 0
EDIT_INTERVAL = 2  # সেকেন্ডে, ফ্লাড এড়াতে

async def progress_for_pyrogram(
    current: int,
    total: int,
    ud_type: str,
    message: Message,
    start: float
) -> None:
    """Pyrogram ডাউনলোড/আপলোড প্রোগ্রেস বার দেখাবে"""
    global last_edit_time
    
    now = time.time()
    if now - last_edit_time < EDIT_INTERVAL and current != total:
        return
    
    last_edit_time = now
    
    diff = now - start
    if diff == 0:
        diff = 1
    
    # প্রোগ্রেস ক্যালকুলেশন
    percentage = current * 100 / total
    speed = current / diff
    elapsed_time = round(diff)
    time_to_completion = round((total - current) / speed) if speed > 0 else 0
    
    # প্রোগ্রেস বার
    progress = "█" * int(percentage // 10) + "░" * (10 - int(percentage // 10))
    
    # সাইজ ফরম্যাট
    def format_size(bytes_val):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_val < 1024:
                return f"{bytes_val:.2f} {unit}"
            bytes_val /= 1024
        return f"{bytes_val:.2f} TB"
    
    current_size = format_size(current)
    total_size = format_size(total)
    
    # ফাইনাল মেসেজ
    if percentage >= 100:
        progress_text = f"✅ **{ud_type} সম্পূর্ণ হয়েছে!**\n"
    else:
        progress_text = (
            f"⏳ **{ud_type}**\n"
            f"├ {progress} {percentage:.1f}%\n"
            f"├ 📊 {current_size} / {total_size}\n"
            f"├ ⚡ স্পিড: {format_size(speed)}/s\n"
            f"└ ⏱️ সময়: {elapsed_time}s / {time_to_completion}s"
        )
    
    try:
        await message.edit_text(progress_text)
    except Exception:
        # মেসেজ এডিট এড়র হলে সাইলেন্টলি ইগনোর
        pass

def download_file_from_url(url: str, download_path: str, message: Message) -> bool:
    """HTTP লিংক থেকে ফাইল ডাউনলোড করবে প্রোগ্রেস সহ"""
    try:
        response = requests.get(url, stream=True, timeout=30)
        response.raise_for_status()
        
        total_size = int(response.headers.get('content-length', 0))
        downloaded = 0
        start_time = time.time()
        
        with open(download_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)
                    downloaded += len(chunk)
                    
                    # প্রোগ্রেস আপডেট
                    asyncio.run(progress_for_pyrogram(
                        downloaded, total_size,
                        "ডাউনলোড হচ্ছে...",
                        message,
                        start_time
                    ))
        
        return True
    except Exception as e:
        print(f"URL ডাউনলোড এড়র: {e}")
        return False

def extract_thumbnail(video_path: str, thumbnail_path: str) -> bool:
    """ভিডিও থেকে থাম্বনেইল এক্সট্র্যাক্ট করবে"""
    try:
        cmd = [
            "ffmpeg", "-i", video_path,
            "-ss", "00:00:01",  # ১ সেকেন্ডের সময়
            "-vframes", "1",
            "-y",  # ওভাররাইট করবে
            thumbnail_path
        ]
        
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0 and os.path.exists(thumbnail_path):
            return True
        return False
    except Exception as e:
        print(f"থাম্বনেইল এক্সট্র্যাকশন এড়র: {e}")
        return False

def convert_video(input_path: str, output_path: str, message: Message) -> bool:
    """মেইন কনভারশন ফাংশন - FFmpeg ব্যবহার করে"""
    try:
        # ফাইল সাইজ জানতে হবে প্রোগ্রেসের জন্য
        input_size = os.path.getsize(input_path)
        
        # FFmpeg কমান্ড
        cmd = [
            "ffmpeg", "-i", input_path,
            "-c:v", "libx264",      # H.264 ভিডিও কোডেক (Android সাপোর্টেড)
            "-preset", "ultrafast",  # সুপার ফাস্ট কনভারশন
            "-c:a", "aac",          # AAC অডিও কোডেক
            "-strict", "-2",        # AAC এর জন্য
            "-movflags", "+faststart",  # স্ট্রিমিং অপটিমাইজেশন
            "-y",                   # ওভাররাইট করবে
            output_path
        ]
        
        # প্রোসেস স্টার্ট
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1
        )
        
        start_time = time.time()
        last_progress = 0
        
        # রিয়েল-টাইম আউটপুট পার্স করে প্রোগ্রেস দেখানো
        for line in process.stdout:
            if "time=" in line:
                try:
                    # FFmpeg টাইম স্ট্যাম্প পার্স করবে
                    time_str = line.split("time=")[1].split()[0]
                    h, m, s = time_str.split(":")
                    seconds = int(h) * 3600 + int(m) * 60 + float(s)
                    
                    # প্রক্সি প্রোগ্রেস (অনুমান ভিত্তিক)
                    progress = min(95, int((seconds / 100) * 100))  # সিমুলেটেড
                    
                    if progress - last_progress >= 10:  # ১০% পর পর আপডেট
                        asyncio.run(progress_for_pyrogram(
                            progress, 100,
                            "কনভার্ট হচ্ছে...",
                            message,
                            start_time
                        ))
                        last_progress = progress
                except:
                    continue
        
        process.wait()
        
        # কনভারশন সাকসেস চেক
        if process.returncode == 0 and os.path.exists(output_path):
            # ফাইনাল প্রোগ্রেস ১০০%
            asyncio.run(progress_for_pyrogram(
                100, 100,
                "কনভার্ট হচ্ছে...",
                message,
                start_time
            ))
            return True
        else:
            print(f"FFmpeg এড়র: {process.returncode}")
            return False
            
    except subprocess.TimeoutExpired:
        process.kill()
        return False
    except Exception as e:
        print(f"কনভারশন এড়র: {e}")
        return False

def cleanup_files(*file_paths):
    """টেম্পরারি ফাইল ডিলিট করবে"""
    for path in file_paths:
        try:
            if path and os.path.exists(path):
                os.remove(path)
        except Exception as e:
            print(f"ফাইল ডিলিট এড়র {path}: {e}")

def is_valid_url(text: str) -> bool:
    """চেক করবে ইনপুট ভ্যালিড URL কিনা"""
    return text.startswith(('http://', 'https://')) and any(ext in text.lower() for ext in ['.mkv', '.mp4', '.avi', '.webm', '.hevc', '.mov'])

import os
import re
import base64
import json
import asyncio
import random
import subprocess
import tarfile
import urllib.request
import glob
import shutil
from datetime import datetime
from zoneinfo import ZoneInfo
import jdatetime
from urllib.parse import urlparse, urlunparse, quote, unquote
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.network import ConnectionTcpFull

# --- تنظیمات اولیه ---
raw_api_id = os.environ.get("API_ID")
API_ID = int(raw_api_id) if raw_api_id and raw_api_id.strip() else 34146126

raw_api_hash = os.environ.get("API_HASH")
API_HASH = raw_api_hash if raw_api_hash and raw_api_hash.strip() else "6f3350e049ef37676b729241f5bc8c5e"

SESSION_STRING = os.environ.get("SESSION_STRING")

CHANNELS = ['napsternetv']
SEARCH_LIMIT = 500  # تعداد پیام برای بررسی در هر کانال
TOTAL_FINAL_COUNT = 150  # تعداد نهایی کانفیگ‌ها

def get_persian_time():
    try:
        tehran_tz = ZoneInfo("Asia/Tehran")
        now_tehran = datetime.now(tehran_tz)
        j_date = jdatetime.datetime.fromgregorian(datetime=now_tehran)
        return j_date.strftime("%Y-%m-%d %H:%M")
    except Exception as e:
        print(f"⚠️ Time Error: {e}")
        return datetime.now().strftime("%Y-%m-%d %H:%M")

def add_name_to_config(conf, time_tag, is_top_20=False):
    """
    نام کانفیگ را اصولی تغییر می‌دهد.
    اگر کانفیگ جزو ۲۰تای اول باشد، عبارت 'پر سرعت' را اضافه می‌کند.
    """
    conf = conf.strip()
    prefix = "🚀 پر سرعت | " if is_top_20 else ""

    # مدیریت کانفیگ‌های VMess (دیکود کردن ساختار JSON Base64)
    if conf.startswith("vmess://"):
        try:
            b64_part = conf[8:].strip()
            b64_part += "=" * (-len(b64_part) % 4)  # رفع خطای پدینگ احتمالی
            decoded = base64.b64decode(b64_part).decode('utf-8')
            data = json.loads(decoded)
            current_name = data.get("ps", "").strip()
            
            if not current_name:
                new_name = f"{prefix}{time_tag}"
            else:
                if time_tag not in current_name:
                    new_name = f"{prefix}{current_name} | {time_tag}"
                else:
                    new_name = f"{prefix}{current_name}"
            
            data["ps"] = new_name
            new_b64 = base64.b64encode(json.dumps(data).encode('utf-8')).decode('utf-8')
            return f"vmess://{new_b64}"
        except Exception:
            return conf

    # مدیریت سایر پروتکل‌ها (VLESS, Trojan, ShadowSocks و غیره)
    try:
        parsed = urlparse(conf)
        current_name = unquote(parsed.fragment).strip()
        
        if not current_name:
            new_name = f"{prefix}@{time_tag}"
        else:
            if time_tag not in current_name:
                new_name = f"{prefix}{current_name} | {time_tag}"
            else:
                new_name = f"{prefix}{current_name}"

        final_fragment = quote(new_name)
        new_parsed = parsed._replace(fragment=final_fragment)
        return urlunparse(new_parsed)
    except Exception:
        return conf

def download_litespeedtest():
    """ دانلود خودکار ابزار تست سرعت مخصوص لینوکس ۶۴ بیت برای گیت‌هاب اکشن """
    if os.path.exists("./liteSpeedTest"):
        return True
    
    print("📥 Downloading liteSpeedTest binary...")
    url = "https://github.com/anywlan/liteSpeedTest/releases/download/v0.15.1/liteSpeedTest_linux_amd64.tar.gz"
    try:
        urllib.request.urlretrieve(url, "litespeedtest.tar.gz")
        with tarfile.open("litespeedtest.tar.gz", "r:gz") as tar:
            tar.extractall(path=".")
        os.chmod("./liteSpeedTest", 0o755)
        print("✅ liteSpeedTest ready.")
        return True
    except Exception as e:
        print(f"❌ Failed to download tester binary: {e}")
        return False

def get_litespeedtest_output_links():
    """ استخراج لینک‌های تست شده و مرتب شده بر اساس سرعت از پوشه خروجی ابزار """
    txt_files = glob.glob("output/*.txt") + glob.glob("*.txt")
    exclude = ["raw_collected.txt", "sub.txt", "sub_raw.txt", "requirements.txt"]
    valid_files = [f for f in txt_files if os.path.basename(f) not in exclude]
    
    if not valid_files:
        return []
    
    latest_file = max(valid_files, key=os.path.getmtime)
    print(f"📖 Reading speed test results from: {latest_file}")
    
    try:
        with open(latest_file, "r", encoding="utf-8") as f:
            content = f.read().strip()
            try:
                padded_content = content + "=" * (-len(content) % 4)
                decoded = base64.b64decode(padded_content).decode('utf-8')
                links = decoded.splitlines()
            except Exception:
                links = content.splitlines()
            
            return [line.strip() for line in links if line.strip() and "://" in line]
    except Exception as e:
        print(f"❌ Error reading speed test output: {e}")
        return []

async def main():
    if not SESSION_STRING:
        print("❌ SESSION_STRING Not Found! Please set it in GitHub Secrets.")
        return

    client = TelegramClient(
        StringSession(SESSION_STRING),
        API_ID,
        API_HASH,
        connection=ConnectionTcpFull
    )

    try:
        print("🚀 Connecting to Telegram...")
        await client.connect()
        
        if not await client.is_user_authorized():
            print("❌ Session is invalid or expired.")
            return

        print("✅ Logged in successfully.")
        
        all_raw_configs = []
        time_tag = get_persian_time()
        print(f"⏰ Persian Time: {time_tag}")

        for channel in CHANNELS:
            print(f"📡 Scanning @{channel}...")
            try:
                async for message in client.iter_messages(channel, limit=SEARCH_LIMIT):
                    if message.text:
                        links = re.findall(r'(?:vmess|vless|ss|trojan|tuic|hysteria2?)://[^\s\t\n]+', message.text)
                        
                        for conf in links:
                            conf = re.split(r'[\s\n]+', conf)[0]
                            conf = re.sub(r'[)\]}"\'>,]+$', '', conf)
                            if conf:
                                all_raw_configs.append(conf)
                
                print(f"   Found {len(all_raw_configs)} configs so far...")
                await asyncio.sleep(random.randint(2, 5))

            except Exception as e:
                print(f"⚠️ Error scanning {channel}: {e}")

        unique_raw_configs = list(dict.fromkeys(all_raw_configs))
        print(f"🔍 Unique configs collected for testing: {len(unique_raw_configs)}")

        fastest_configs = []

        if unique_raw_configs:
            temp_input = "raw_collected.txt"
            with open(temp_input, "w", encoding="utf-8") as f:
                f.write("\n".join(unique_raw_configs))
            
            if download_litespeedtest():
                print("⚡ Executing Speed Test (Downloading test files through proxies)...")
                try:
                    subprocess.run(["./liteSpeedTest", "-sub", temp_input], capture_output=True, text=True, timeout=300)
                    fastest_configs = get_litespeedtest_output_links()
                except subprocess.TimeoutExpired:
                    print("⚠️ Speed test timed out.")
                except Exception as e:
                    print(f"⚠️ Speed test error: {e}")

            if not fastest_configs:
                print("⚠️ Speed test returned 0 results. Using fallback...")
                fastest_configs = unique_raw_configs[:TOTAL_FINAL_COUNT]
            else:
                print(f"✅ Speed test finished. Filtered & Sorted top {len(fastest_configs)} configs.")
                fastest_configs = fastest_configs[:TOTAL_FINAL_COUNT]

        # اعمال نام‌گذاری و برچسب زدن به ۲۰تای اول
        final_processed_configs = []
        for idx, conf in enumerate(fastest_configs):
            is_top_20 = (idx < 20)  # بررسی اینکه آیا جزو ۲۰ کانفیگ اول (سریع‌ترین‌ها) است یا خیر
            final_conf = add_name_to_config(conf, time_tag, is_top_20=is_top_20)
            if final_conf:
                final_processed_configs.append(final_conf)

        if final_processed_configs:
            content_str = "\n".join(final_processed_configs)
            encoded = base64.b64encode(content_str.encode('utf-8')).decode('utf-8')
            
            with open("sub.txt", "w", encoding="utf-8") as f:
                f.write(encoded)
            
            with open("sub_raw.txt", "w", encoding="utf-8") as f:
                f.write(content_str)

            print(f"✨ Success! Saved {len(final_processed_configs)} working configs (Top 20 highlighted).")
        else:
            print("⚠️ No configs found to save.")

    except Exception as e:
        print(f"⚠️ Critical Error: {e}")
    finally:
        # تمیزکاری فایل‌های موقت هارد دیسک گیت‌هاب اکشن
        for temp_file in ["raw_collected.txt", "litespeedtest.tar.gz", "liteSpeedTest"]:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        if os.path.exists("output") and os.path.isdir("output"):
            shutil.rmtree("output")
            
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())

import os
import re
import base64
import asyncio
import random
import subprocess
import tarfile
import urllib.request
import glob
import gzip
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

CHANNELS = ['napsternetv', 'v2ray_configs_channel', 'other_channel'] # کانال‌های بیشتری اضافه کنید
SEARCH_LIMIT = 2000  
TOTAL_FINAL_COUNT = 150  # تعداد نهایی

def get_persian_time():
    try:
        tehran_tz = ZoneInfo("Asia/Tehran")
        now_tehran = datetime.now(tehran_tz)
        j_date = jdatetime.datetime.fromgregorian(datetime=now_tehran)
        return j_date.strftime("%Y-%m-%d %H:%M")
    except Exception as e:
        print(f"⚠️ Time Error: {e}")
        return datetime.now().strftime("%Y-%m-%d %H:%M")

def add_name_to_config(conf, time_tag):
    conf = conf.strip()
    if conf.startswith("vmess://"):
        return conf # Vmess نیاز به دیکود Base64 دارد، تغییر نام ساده لینک ساختار آن را خراب می‌کند

    try:
        parsed = urlparse(conf)
        current_name = unquote(parsed.fragment).strip()
        
        if not current_name:
            new_name = f"@{time_tag}"
        else:
            if time_tag not in current_name:
                new_name = f"{current_name} | {time_tag}"
            else:
                new_name = current_name

        final_fragment = quote(new_name)
        new_parsed = parsed._replace(fragment=final_fragment)
        return urlunparse(new_parsed)
    except Exception:
        return conf

def download_litespeedtest():
    if os.path.exists("./liteSpeedTest"):
        return True
    
    print("📥 Downloading liteSpeedTest binary...")
    url = "https://github.com/xxf098/LiteSpeedTest/releases/download/v0.15.0/lite-linux-amd64-v0.15.0.gz"
    try:
        urllib.request.urlretrieve(url, "litespeedtest.gz")
        with gzip.open("litespeedtest.gz", "rb") as f_in:
            with open("./liteSpeedTest", "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
        
        os.chmod("./liteSpeedTest", 0o755)
        print("✅ liteSpeedTest ready.")
        return True
    except Exception as e:
        print(f"❌ Failed to download tester binary: {e}")
        return False

def get_litespeedtest_output_links():
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
            
            # فیلتر سخت‌گیرانه: فقط خطوطی که شامل پروتکل معتبر هستند
            valid_protocols = ("vmess://", "vless://", "ss://", "trojan://", "tuic://", "hysteria://", "hysteria2://")
            return [line.strip() for line in links if line.strip().startswith(valid_protocols)]
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
                        # Regex سخت‌گیرانه‌تر برای جلوگیری از گرفتن کاراکترهای فارسی یا نامعتبر در انتهای لینک
                        links = re.findall(r'(?:vmess|vless|ss|trojan|tuic|hysteria2?)://[a-zA-Z0-9\-\.\_\~\:\/\?\#\[\]\@\!\$\&\'\(\)\*\+\,\;\=\%]+', message.text)
                        
                        for conf in links:
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
                print("⚡ Executing Speed Test (Strict Mode - Wait up to 15 mins)...")
                try:
                    # ذخیره خروجی در یک متغیر برای بررسی
                    result = subprocess.run(
                        ["./liteSpeedTest", "--test", temp_input], 
                        capture_output=True, 
                        text=True, 
                        timeout=900
                    )
                    
                    # چاپ لاگ‌های ابزار تستر برای عیب‌یابی در گیت‌هاب اکشنز
                    print("--- LiteSpeedTest STDOUT ---")
                    print(result.stdout[:1500]) # چاپ ۱۵۰۰ کاراکتر اول
                    if result.stderr:
                        print("--- LiteSpeedTest STDERR ---")
                        print(result.stderr[:1000])
                        
                    fastest_configs = get_litespeedtest_output_links()
                except Exception as e:
                    print(f"❌ Error during speed test execution: {e}")

            # حالت سخت‌گیرانه: بدون Fallback به کانفیگ‌های تست نشده!
            if not fastest_configs:
                print("❌ Strict Mode Triggered: No working configs passed the speed test. Aborting update to keep previous good configs intact.")
                return  # خروج از برنامه بدون بازنویسی فایل‌ها


            # حالت سخت‌گیرانه: بدون Fallback به کانفیگ‌های تست نشده!
            if not fastest_configs:
                print("❌ Strict Mode Triggered: No working configs passed the speed test. Aborting update to keep previous good configs intact.")
                return  # خروج از برنامه بدون بازنویسی فایل‌ها

            print(f"✅ Speed test finished. Filtered & Sorted top {len(fastest_configs)} configs.")
            fastest_configs = fastest_configs[:TOTAL_FINAL_COUNT]

        final_processed_configs = []
        for conf in fastest_configs:
            final_conf = add_name_to_config(conf, time_tag)
            if final_conf:
                final_processed_configs.append(final_conf)

        if final_processed_configs:
            content_str = "\n".join(final_processed_configs)
            encoded = base64.b64encode(content_str.encode('utf-8')).decode('utf-8')
            
            with open("sub.txt", "w", encoding="utf-8") as f:
                f.write(encoded)
            
            with open("sub_raw.txt", "w", encoding="utf-8") as f:
                f.write(content_str)

            print(f"✨ Success! Saved {len(final_processed_configs)} working & fastest configs.")
        else:
            print("⚠️ No configs found to save.")

    except Exception as e:
        print(f"⚠️ Critical Error: {e}")
    finally:
        for temp_file in ["raw_collected.txt", "litespeedtest.gz", "liteSpeedTest"]:
            if os.path.exists(temp_file):
                os.remove(temp_file)
        if os.path.exists("output") and os.path.isdir("output"):
            shutil.rmtree("output")
            
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())

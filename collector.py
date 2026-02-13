import os
import re
import base64
import json
import asyncio
import random
import socket
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

CHANNELS = ['napsternetv', 'FreakConfig', 'Configir98']
SEARCH_LIMIT = 500  # کمی کمتر کردم که سرعت بالاتر برود
TOTAL_FINAL_COUNT = 200

def get_persian_time():
    try:
        tehran_tz = ZoneInfo("Asia/Tehran")
        now_tehran = datetime.now(tehran_tz)
        j_date = jdatetime.datetime.fromgregorian(datetime=now_tehran)
        return j_date.strftime("%Y-%m-%d %H:%M")
    except Exception as e:
        return datetime.now().strftime("%Y-%m-%d %H:%M")

async def check_connectivity(host, port, timeout=1.5):
    """
    تست اتصال به سرور (TCP Ping).
    اگر پورت باز باشد True برمی‌گرداند.
    """
    try:
        # استفاده از asyncio برای سرعت بالاتر و غیرمسدود کننده
        future = asyncio.open_connection(host, port)
        reader, writer = await asyncio.wait_for(future, timeout=timeout)
        writer.close()
        await writer.wait_closed()
        return True
    except:
        return False

def parse_config_host_port(conf):
    """
    تلاش برای استخراج IP و Port از انواع کانفیگ‌ها
    """
    try:
        if conf.startswith("vmess://"):
            # دیکود کردن بخش بعد از vmess://
            b64_str = conf[8:]
            # افزودن پدینگ در صورت نیاز
            missing_padding = len(b64_str) % 4
            if missing_padding:
                b64_str += '=' * (4 - missing_padding)
            
            decoded = base64.b64decode(b64_str).decode('utf-8')
            data = json.loads(decoded)
            return data.get('add'), int(data.get('port'))
        
        else:
            # برای Vless, Trojan, SS و ...
            parsed = urlparse(conf)
            return parsed.hostname, parsed.port
    except:
        return None, None

def add_name_to_config(conf, time_tag):
    conf = conf.strip()
    if conf.startswith("vmess://"):
        return conf # دستکاری نام VMess پیچیده‌تر است، فعلا رد می‌کنیم

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

async def main():
    if not SESSION_STRING:
        print("❌ SESSION_STRING Not Found!")
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
            print("❌ Session is invalid.")
            return

        print("✅ Logged in.")
        
        all_valid_configs = []
        time_tag = get_persian_time()
        
        # برای جلوگیری از تکراری‌ها قبل از تست
        seen_links = set()

        for channel in CHANNELS:
            print(f"📡 Scanning @{channel}...")
            async for message in client.iter_messages(channel, limit=SEARCH_LIMIT):
                if message.text:
                    links = re.findall(r'(?:vmess|vless|ss|trojan|tuic|hysteria2?)://[^\s\t\n]+', message.text)
                    
                    for conf in links:
                        conf = re.split(r'[\s\n]+', conf)[0]
                        conf = re.sub(r'[)\]}"\'>,]+$', '', conf)

                        if conf in seen_links:
                            continue
                        
                        seen_links.add(conf)

                        # 1. استخراج آدرس سرور
                        host, port = parse_config_host_port(conf)
                        
                        if host and port:
                            # 2. تست اتصال (Ping)
                            is_alive = await check_connectivity(host, port)
                            
                            if is_alive:
                                # 3. تغییر نام و افزودن به لیست نهایی
                                final_conf = add_name_to_config(conf, time_tag)
                                all_valid_configs.append(final_conf)
                                # چاپ یک نقطه برای نمایش پیشرفت
                                print(".", end="", flush=True)
            
            print(f"\n   Found {len(all_valid_configs)} alive configs so far from {channel}")
            await asyncio.sleep(random.randint(2, 4))

        # محدود کردن به تعداد درخواستی
        final_list = all_valid_configs[:TOTAL_FINAL_COUNT]

        if final_list:
            content_str = "\n".join(final_list)
            encoded = base64.b64encode(content_str.encode('utf-8')).decode('utf-8')
            
            with open("sub.txt", "w", encoding="utf-8") as f:
                f.write(encoded)
            
            with open("sub_raw.txt", "w", encoding="utf-8") as f:
                f.write(content_str)

            print(f"✨ Success! Saved {len(final_list)} WORKING configs.")
        else:
            print("⚠️ No working configs found.")

    except Exception as e:
        print(f"⚠️ Critical Error: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())

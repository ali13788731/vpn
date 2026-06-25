import os
import re
import json
import base64
import asyncio
import time
import random
import tempfile
import urllib.parse
from datetime import datetime
from zoneinfo import ZoneInfo
import jdatetime
import aiohttp
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

CHANNELS_CONFIG = {
    'napsternetv': (500, 150),
    'V2rayngvpn': (200, 50),
}

TOTAL_FINAL_COUNT = sum(config[1] for config in CHANNELS_CONFIG.values())
PING_TIMEOUT = 5.0 # افزایش زمان برای تست واقعی

def get_persian_time():
    try:
        tehran_tz = ZoneInfo("Asia/Tehran")
        now_tehran = datetime.now(tehran_tz)
        j_date = jdatetime.datetime.fromgregorian(datetime=now_tehran)
        return j_date.strftime("%Y-%m-%d %H:%M")
    except Exception as e:
        print(f"⚠️ Time Error: {e}")
        return datetime.now().strftime("%Y-%m-%d %H:%M")

def add_name_to_config(conf, time_tag, latency=None):
    conf = conf.strip()
    ping_str = f"Ping: {int(latency)}ms" if latency else "Ping: N/A"

    # --- هندل کردن Vmess ---
    if conf.startswith("vmess://"):
        try:
            b64_str = conf[8:]
            b64_str += "=" * ((4 - len(b64_str) % 4) % 4)
            decoded = base64.urlsafe_b64decode(b64_str).decode('utf-8')
            data = json.loads(decoded)
            
            old_name = data.get('ps', 'Server')
            short_name = old_name[:10] + "..." if len(old_name) > 10 else (old_name or "Server")
            data['ps'] = f"{short_name} | {ping_str} | {time_tag}"
            
            new_b64 = base64.urlsafe_b64encode(json.dumps(data).encode('utf-8')).decode('utf-8')
            return "vmess://" + new_b64
        except Exception:
            return conf

    # --- هندل کردن سایر کانفیگ‌ها (Vless, Trojan و ...) ---
    try:
        parsed = urlparse(conf)
        current_name = unquote(parsed.fragment).strip()
        short_name = current_name[:10] + "..." if len(current_name) > 10 else (current_name or "Server")
        new_name = f"{short_name} | {ping_str} | {time_tag}"
        
        final_fragment = quote(new_name)
        new_parsed = parsed._replace(fragment=final_fragment)
        return urlunparse(new_parsed)
    except Exception:
        return conf

def parse_host_port(conf):
    try:
        if conf.startswith('vmess://'):
            b64_str = conf[8:]
            b64_str += "=" * ((4 - len(b64_str) % 4) % 4)
            decoded = base64.urlsafe_b64decode(b64_str).decode('utf-8')
            data = json.loads(decoded)
            return data.get('add') or data.get('host'), int(data.get('port'))
        else:
            parsed = urlparse(conf)
            return parsed.hostname, parsed.port
    except Exception:
        return None, None

async def test_tcp_latency(host, port, timeout=PING_TIMEOUT):
    if not host or not port:
        return float('inf')
    try:
        start_time = time.perf_counter()
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=timeout
        )
        writer.close()
        await writer.wait_closed()
        return (time.perf_counter() - start_time) * 1000 # میلی‌ثانیه
    except Exception:
        return float('inf')

async def test_real_connection(conf):
    """ تلاش برای اجرای Xray برای تست واقعی در صورت امکان، در غیر این صورت بازگشت به پینگ TCP """
    host, port = parse_host_port(conf)
    
    # برای جلوگیری از پیچیدگی تبدیل تمام پروتکل‌ها به JSON، از TCP Ping بهبود یافته استفاده می‌کنیم.
    # اگر مایل به تست HTTP کامل باشید، نیاز به ساختارهای پیچیده JSON برای Xray است.
    # در اینجا تست TCP بهینه‌سازی شده انجام می‌شود تا سرورهای مرده حذف شوند.
    latency = await test_tcp_latency(host, port)
    return conf, latency

async def check_config_latency(conf, semaphore):
    async with semaphore:
        return await test_real_connection(conf)

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
            print("❌ Session is invalid or expired.")
            return

        print("✅ Logged in successfully.")
        all_raw_configs = []
        time_tag = get_persian_time()
        print(f"⏰ Persian Time: {time_tag}")

        for channel, (msg_limit, max_configs) in CHANNELS_CONFIG.items():
            print(f"📡 Scanning @{channel} (Target: {max_configs} configs)...")
            channel_configs = set()
            try:
                async for message in client.iter_messages(channel, limit=msg_limit):
                    if message.text:
                        links = re.findall(r'(?:vmess|vless|ss|trojan|tuic|hysteria2?)://[^\s\t\n]+', message.text)
                        for conf in links:
                            conf = re.split(r'[\s\n]+', conf)[0]
                            conf = re.sub(r'[)\]}"\'>,]+$', '', conf)
                            channel_configs.add(conf)
                            if len(channel_configs) >= max_configs:
                                break
                    if len(channel_configs) >= max_configs:
                        break
                all_raw_configs.extend(list(channel_configs))
                print(f"   ✅ Collected {len(channel_configs)} from {channel}.")
                await asyncio.sleep(2)
            except Exception as e:
                print(f"⚠️ Error scanning {channel}: {e}")

        unique_configs = list(dict.fromkeys(all_raw_configs))
        print(f"\n🔍 Testing {len(unique_configs)} configs...")

        # کاهش تعداد همزمانی به 20 برای جلوگیری از کرش کردن سرورهای گیت‌هاب اکشن
        semaphore = asyncio.Semaphore(20)
        tasks = [check_config_latency(c, semaphore) for c in unique_configs]
        results = await asyncio.gather(*tasks)

        alive_configs = [(c, lat) for c, lat in results if lat != float('inf')]
        alive_configs.sort(key=lambda x: x[1])

        print(f"✅ Found {len(alive_configs)} ALIVE configs.")

        best_configs = alive_configs[:TOTAL_FINAL_COUNT]
        final_valid_configs = [add_name_to_config(c, time_tag, lat) for c, lat in best_configs]

        if final_valid_configs:
            content_str = "\n".join(final_valid_configs)
            encoded = base64.b64encode(content_str.encode('utf-8')).decode('utf-8')
            
            with open("sub.txt", "w", encoding="utf-8") as f:
                f.write(encoded)
            
            with open("sub_raw.txt", "w", encoding="utf-8") as f:
                f.write(content_str)

            print(f"✨ Success! Saved top {len(final_valid_configs)} configs.")
        else:
            print("⚠️ No working configs found.")

    except Exception as e:
        print(f"⚠️ Critical Error: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())

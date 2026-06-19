import os
import re
import json
import base64
import asyncio
import time
import random
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
TOTAL_FINAL_COUNT = 150 # تعداد نهایی کانفیگ‌ها
PING_TIMEOUT = 3.0 # حداکثر زمان انتظار برای پینگ (ثانیه)

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
    """ نام کانفیگ را به همراه تگ زمانی و پینگ (اختیاری) تغییر می‌دهد """
    conf = conf.strip()
    if conf.startswith("vmess://"):
        # تغییر نام vmess نیازمند دی‌کد و انکود مجدد جیسون است که در این اسکریپت ساده از آن چشم‌پوشی می‌کنیم
        return conf

    try:
        parsed = urlparse(conf)
        current_name = unquote(parsed.fragment).strip()
        
        ping_str = f" [Ping: {int(latency*1000)}ms]" if latency else ""

        if not current_name:
            new_name = f"@{time_tag}{ping_str}"
        else:
            if time_tag not in current_name:
                new_name = f"{current_name} | {time_tag}{ping_str}"
            else:
                new_name = f"{current_name}{ping_str}"

        final_fragment = quote(new_name)
        new_parsed = parsed._replace(fragment=final_fragment)
        return urlunparse(new_parsed)
    except Exception:
        return conf

def parse_host_port(conf):
    """ استخراج IP و Port از کانفیگ برای تست پینگ """
    try:
        if conf.startswith('vmess://'):
            b64_str = conf[8:]
            # اصلاح پدینگ Base64 در صورت نیاز
            b64_str += "=" * ((4 - len(b64_str) % 4) % 4)
            decoded = base64.b64decode(b64_str).decode('utf-8')
            data = json.loads(decoded)
            return data.get('add') or data.get('host'), int(data.get('port'))
        else:
            parsed = urlparse(conf)
            return parsed.hostname, parsed.port
    except Exception:
        return None, None

async def test_tcp_latency(host, port, timeout=PING_TIMEOUT):
    """ تست سرعت اتصال به سرور """
    if not host or not port:
        return float('inf')
    try:
        start_time = time.perf_counter()
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, port), timeout=timeout
        )
        writer.close()
        await writer.wait_closed()
        return time.perf_counter() - start_time
    except Exception:
        return float('inf')

async def check_config_latency(conf, semaphore):
    """ بررسی یک کانفیگ با کنترل همزمانی """
    async with semaphore:
        host, port = parse_host_port(conf)
        latency = await test_tcp_latency(host, port)
        return conf, latency

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

        # مرحله 1: جمع‌آوری کانفیگ‌ها
        for channel in CHANNELS:
            print(f"📡 Scanning @{channel}...")
            try:
                async for message in client.iter_messages(channel, limit=SEARCH_LIMIT):
                    if message.text:
                        links = re.findall(r'(?:vmess|vless|ss|trojan|tuic|hysteria2?)://[^\s\t\n]+', message.text)
                        for conf in links:
                            conf = re.split(r'[\s\n]+', conf)[0]
                            conf = re.sub(r'[)\]}"\'>,]+$', '', conf)
                            all_raw_configs.append(conf)
                
                print(f"   found {len(all_raw_configs)} raw configs so far...")
                await asyncio.sleep(random.randint(2, 5))

            except Exception as e:
                print(f"⚠️ Error scanning {channel}: {e}")

        # حذف تکراری‌ها
        unique_configs = list(dict.fromkeys(all_raw_configs))
        print(f"🔍 Testing {len(unique_configs)} unique configs for TCP latency...")

        # مرحله 2: تست سرعت کانفیگ‌ها به صورت همزمان (حداکثر 50 اتصال همزمان)
        semaphore = asyncio.Semaphore(50)
        tasks = [check_config_latency(c, semaphore) for c in unique_configs]
        results = await asyncio.gather(*tasks)

        # مرحله 3: فیلتر کردن سرورهای زنده و مرتب‌سازی بر اساس کمترین پینگ
        alive_configs = [(conf, lat) for conf, lat in results if lat != float('inf')]
        alive_configs.sort(key=lambda x: x[1]) # مرتب‌سازی از سریع‌ترین به کندترین

        print(f"✅ Found {len(alive_configs)} ALIVE configs.")

        # انتخاب 150 تای برتر و اعمال تغییر نام
        best_configs = alive_configs[:TOTAL_FINAL_COUNT]
        final_valid_configs = [add_name_to_config(conf, time_tag, lat) for conf, lat in best_configs]

        # مرحله 4: ذخیره‌سازی
        if final_valid_configs:
            content_str = "\n".join(final_valid_configs)
            encoded = base64.b64encode(content_str.encode('utf-8')).decode('utf-8')
            
            with open("sub.txt", "w", encoding="utf-8") as f:
                f.write(encoded)
            
            with open("sub_raw.txt", "w", encoding="utf-8") as f:
                f.write(content_str)

            print(f"✨ Success! Saved top {len(final_valid_configs)} fastest configs.")
        else:
            print("⚠️ No working configs found.")

    except Exception as e:
        print(f"⚠️ Critical Error: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())

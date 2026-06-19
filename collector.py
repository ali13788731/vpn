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

# تنظیمات پیشرفته کانال‌ها
# فرمت: 'آیدی_کانال': (تعداد_پیام_برای_بررسی, حداکثر_خروجی_از_این_کانال)
CHANNELS_CONFIG = {
    'napsternetv': (500, 150),   # ۳۰۰ پیام آخر رو بگرد، نهایتاً ۲۰ کانفیگ خروجی بده
    'V2rayngvpn': (200, 50),   # می‌تونی کانال‌های دیگه رو با تنظیمات متفاوت اینجا اضافه کنی
}

TOTAL_FINAL_COUNT = sum(config[1] for config in CHANNELS_CONFIG.values())
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
    """ نام کانفیگ را تغییر می‌دهد: اسم کوتاه... | پینگ | تاریخ و ساعت """
    conf = conf.strip()
    
    # برای vmess نیاز به دی‌کد و انکود مجدد جیسون است که اینجا رد می‌شویم
    if conf.startswith("vmess://"):
        return conf

    try:
        parsed = urlparse(conf)
        current_name = unquote(parsed.fragment).strip()
        
        # ۱. مرتب‌سازی و کوتاه کردن اسم
        if current_name:
            # نمایش حداکثر ۱۰ کاراکتر اول و افزودن سه نقطه
            short_name = current_name[:10] + "..." if len(current_name) > 10 else current_name
        else:
            # اگر کانفیگ اصلا اسمی نداشت
            short_name = "Server" 

        # ۲. آماده‌سازی بخش پینگ
        ping_str = f"Ping: {int(latency*1000)}ms" if latency else "Ping: N/A"

        # ۳. ترکیب نهایی با فرمت دلخواه شما
        # خروجی نمونه: MyServerVa... | Ping: 120ms | 2026-06-19 10:23
        new_name = f"{short_name} | {ping_str} | {time_tag}"

        final_fragment = quote(new_name)
        new_parsed = parsed._replace(fragment=final_fragment)
        return urlunparse(new_parsed)
        
    except Exception:
        # اگر خطایی رخ داد، همان کانفیگ اولیه را برگردان
        return conf

def parse_host_port(conf):
    """ استخراج IP و Port از کانفیگ برای تست پینگ """
    try:
        if conf.startswith('vmess://'):
            b64_str = conf[8:]
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

        # مرحله 1: جمع‌آوری کانفیگ‌ها بر اساس تنظیمات هر کانال
        for channel, (msg_limit, max_configs) in CHANNELS_CONFIG.items():
            print(f"📡 Scanning @{channel} (Checking {msg_limit} msgs, Target: {max_configs} configs)...")
            channel_configs = set() # استفاده از set برای جلوگیری از تکراری‌های همان کانال
            try:
                async for message in client.iter_messages(channel, limit=msg_limit):
                    if message.text:
                        links = re.findall(r'(?:vmess|vless|ss|trojan|tuic|hysteria2?)://[^\s\t\n]+', message.text)
                        for conf in links:
                            conf = re.split(r'[\s\n]+', conf)[0]
                            conf = re.sub(r'[)\]}"\'>,]+$', '', conf)
                            
                            channel_configs.add(conf)
                            
                            # توقف استخراج اگر به سقف تعیین شده برای این کانال رسیدیم
                            if len(channel_configs) >= max_configs:
                                break
                    
                    if len(channel_configs) >= max_configs:
                        break # شکستن حلقه پیام‌ها
                
                all_raw_configs.extend(list(channel_configs))
                print(f"   ✅ Collected {len(channel_configs)} configs from {channel}.")
                await asyncio.sleep(random.randint(2, 5))

            except Exception as e:
                print(f"⚠️ Error scanning {channel}: {e}")

        # حذف تکراری‌های احتمالی بین کانال‌های مختلف
        unique_configs = list(dict.fromkeys(all_raw_configs))
        print(f"\n🔍 Testing {len(unique_configs)} unique configs for TCP latency...")

        # مرحله 2: تست سرعت کانفیگ‌ها به صورت همزمان
        semaphore = asyncio.Semaphore(50)
        tasks = [check_config_latency(c, semaphore) for c in unique_configs]
        results = await asyncio.gather(*tasks)

        # مرحله 3: فیلتر کردن سرورهای زنده و مرتب‌سازی
        alive_configs = [(conf, lat) for conf, lat in results if lat != float('inf')]
        alive_configs.sort(key=lambda x: x[1]) # از سریع‌ترین به کندترین

        print(f"✅ Found {len(alive_configs)} ALIVE configs.")

        # انتخاب بهترین‌ها بر اساس محدودیت کل (TOTAL_FINAL_COUNT)
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

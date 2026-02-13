import os
import re
import base64
import json
import asyncio
import socket
import random
from datetime import datetime
from zoneinfo import ZoneInfo
import jdatetime
from urllib.parse import urlparse, unquote, quote, urlunparse
from telethon import TelegramClient
from telethon.sessions import StringSession

# --- تنظیمات ---
CHANNELS = [
    'napsternetv', 'FreakConfig', 'Configir98', 
    'V2rayNGn', 'free_v2rayyy', 'DirectVPN', 
    'v2rayng_org', 'v2ray_outlineir'
]
SEARCH_LIMIT = 100 
MAX_TO_TEST = 100 # تعداد کانفیگ برای تست
FINAL_COUNT = 40  # تعداد نهایی برای ذخیره
TIMEOUT = 3       # ثانیه انتظار برای تست اتصال

def get_persian_time():
    try:
        tehran_tz = ZoneInfo("Asia/Tehran")
        now_tehran = datetime.now(tehran_tz)
        return jdatetime.datetime.fromgregorian(datetime=now_tehran).strftime("%Y-%m-%d %H:%M")
    except: return datetime.now().strftime("%Y-%m-%d %H:%M")

def clean_vmess(conf):
    """دی‌کد کردن لینک‌های vmess برای استخراج IP و Port"""
    try:
        if not conf.startswith("vmess://"): return None
        b64 = conf.replace("vmess://", "")
        # اصلاح پدینگ Base64
        padding = len(b64) % 4
        if padding: b64 += "=" * (4 - padding)
        
        decoded = base64.b64decode(b64).decode('utf-8')
        data = json.loads(decoded)
        return data.get('add'), data.get('port'), conf
    except:
        return None

def parse_config(conf):
    """استخراج هاست و پورت از انواع لینک‌ها"""
    try:
        # اگر Vmess بود
        if conf.startswith("vmess://"):
            return clean_vmess(conf)
            
        # اگر Vless/Trojan/SS بود
        parsed = urlparse(conf)
        host = parsed.hostname
        port = parsed.port
        if host and port:
            return host, port, conf
    except: pass
    return None

async def check_connection(host, port):
    """تست اتصال واقعی با سوکت (سریع و دقیق)"""
    try:
        # اجرا در ترد جداگانه برای جلوگیری از قفل شدن برنامه
        loop = asyncio.get_running_loop()
        start = loop.time()
        
        # تلاش برای اتصال TCP
        await asyncio.wait_for(
            loop.sock_connect(socket.socket(socket.AF_INET, socket.SOCK_STREAM), (host, int(port))),
            timeout=TIMEOUT
        )
        return True
    except:
        return False

async def main():
    API_ID = int(os.environ.get("API_ID", 34146126))
    API_HASH = os.environ.get("API_HASH", "6f3350e049ef37676b729241f5bc8c5e")
    SESSION_STRING = os.environ.get("SESSION_STRING")
    
    if not SESSION_STRING:
        print("❌ Error: SESSION_STRING missing.")
        return

    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    
    try:
        print("🚀 Connecting to Telegram...")
        await client.connect()
        
        raw_links = []
        
        # ۱. جمع‌آوری لینک‌ها
        for channel in CHANNELS:
            print(f"📥 Scanning: {channel}")
            try:
                async for message in client.iter_messages(channel, limit=SEARCH_LIMIT):
                    if message.text:
                        found = re.findall(r'(?:vmess|vless|ss|trojan|tuic)://[a-zA-Z0-9\-\._~:/\?#\[\]@!$&\'\(\)\*\+,;=%]+', message.text)
                        for link in found:
                            raw_links.append(link.split()[0]) # تمیزکاری اولیه
            except Exception as e:
                print(f"⚠️ Skip {channel}: {e}")

        unique_links = list(set(raw_links))
        print(f"📊 Found {len(unique_links)} unique links. Parsing...")

        # ۲. پردازش و استخراج IPها
        parsed_configs = []
        for link in unique_links:
            res = parse_config(link)
            if res:
                parsed_configs.append(res) # (host, port, original_link)

        # شافل کردن برای تنوع
        random.shuffle(parsed_configs)
        targets = parsed_configs[:MAX_TO_TEST]

        print(f"🔍 Testing connectivity for {len(targets)} servers...")

        # ۳. تست سرعت بالا (همزمان)
        valid_configs = []
        
        # تابع کمکی برای تسک
        async def tester(target):
            host, port, link = target
            if not host or not port: return None
            # فیلتر کردن لوکال هاست
            if "127.0.0.1" in host or "localhost" in host: return None
            
            is_up = await check_connection(host, port)
            if is_up:
                print(f"✅ UP: {host}:{port}")
                return link
            else:
                return None

        # اجرای تست‌ها
        tasks = [tester(t) for t in targets]
        results = await asyncio.gather(*tasks)
        
        valid_configs = [r for r in results if r is not None]
        
        # ۴. ذخیره‌سازی
        if valid_configs:
            valid_configs = valid_configs[:FINAL_COUNT]
            time_tag = get_persian_time()
            
            # اضافه کردن نام به کانفیگ‌ها
            final_list = []
            for conf in valid_configs:
                # برای Vless/Trojan نام را عوض میکنیم
                if not conf.startswith("vmess://"):
                    try:
                        parsed = urlparse(conf)
                        new_conf = urlunparse(parsed._replace(fragment=quote(f"IR_Gold | {time_tag}")))
                        final_list.append(new_conf)
                    except: final_list.append(conf)
                else:
                    final_list.append(conf)

            content = "\n".join(final_list)
            
            with open("sub.txt", "w") as f:
                f.write(base64.b64encode(content.encode()).decode())
            with open("sub_raw.txt", "w") as f:
                f.write(content)
                
            print(f"🎉 SUCCESS: {len(final_list)} configs saved!")
        else:
            print("❌ Zero working configs found. Check your internet or channels.")
            with open("sub.txt", "w") as f: f.write("")

    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())

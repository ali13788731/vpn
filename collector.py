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
from urllib.parse import urlparse, quote, urlunparse
from telethon import TelegramClient
from telethon.sessions import StringSession

# --- تنظیمات سرعت ---
CHANNELS = ['napsternetv', 'FreakConfig', 'Configir98', 'V2rayNGn', 'free_v2rayyy', 'v2rayng_org']
SEARCH_LIMIT = 40  # کاهش تعداد پیام برای افزایش سرعت (فقط جدیدترین‌ها)
MAX_TO_TEST = 60   # تعداد تست همزمان
FINAL_COUNT = 30 
TIMEOUT = 2        # کاهش زمان انتظار برای هر تست (اگر در ۲ ثانیه وصل نشود، یعنی کنده)

def get_persian_time():
    try:
        tehran_tz = ZoneInfo("Asia/Tehran")
        now_tehran = datetime.now(tehran_tz)
        return jdatetime.datetime.fromgregorian(datetime=now_tehran).strftime("%Y-%m-%d %H:%M")
    except: return datetime.now().strftime("%Y-%m-%d %H:%M")

def parse_config(conf):
    try:
        if conf.startswith("vmess://"):
            b64 = conf.replace("vmess://", "")
            padding = len(b64) % 4
            if padding: b64 += "=" * (4 - padding)
            data = json.loads(base64.b64decode(b64).decode('utf-8'))
            return data.get('add'), data.get('port'), conf
        parsed = urlparse(conf)
        if parsed.hostname and parsed.port:
            return parsed.hostname, parsed.port, conf
    except: pass
    return None

async def check_connection(target):
    host, port, link = target
    try:
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(host, int(port)), timeout=TIMEOUT
        )
        writer.close()
        await writer.wait_closed()
        return link
    except: return None

async def scrape_channel(client, channel):
    """اسکن سریع یک کانال"""
    links = []
    try:
        async for message in client.iter_messages(channel, limit=SEARCH_LIMIT):
            if message.text:
                found = re.findall(r'(?:vmess|vless|ss|trojan|tuic)://[^\s\t\n]+', message.text)
                links.extend([l.rstrip(')]}"\'>,') for l in found])
    except: pass
    return links

async def main():
    API_ID = int(os.environ.get("API_ID", 34146126))
    API_HASH = os.environ.get("API_HASH", "6f3350e049ef37676b729241f5bc8c5e")
    SESSION_STRING = os.environ.get("SESSION_STRING")
    
    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    await client.connect()
    
    # ۱. اسکن همزمان تمام کانال‌ها (Parallel Scraping)
    print("⚡️ Fast Scraping...")
    tasks = [scrape_channel(client, ch) for ch in CHANNELS]
    results = await asyncio.gather(*tasks)
    
    raw_links = list(set([item for sublist in results for item in sublist]))
    print(f"📊 Extracted {len(raw_links)} links.")

    # ۲. آماده‌سازی برای تست
    parsed = [parse_config(l) for l in raw_links if parse_config(l)]
    random.shuffle(parsed)
    targets = parsed[:MAX_TO_TEST]

    # ۳. تست همزمان اتصال (Parallel Testing)
    print(f"🔍 Testing {len(targets)} servers...")
    test_tasks = [check_connection(t) for t in targets]
    valid_configs = await asyncio.gather(*test_tasks)
    
    final_configs = [c for c in valid_configs if c][:FINAL_COUNT]

    # ۴. ذخیره‌سازی
    if final_configs:
        time_tag = get_persian_time()
        output = []
        for c in final_configs:
            if not c.startswith("vmess://"):
                p = urlparse(c)
                output.append(urlunparse(p._replace(fragment=quote(f"IR_FAST | {time_tag}"))))
            else: output.append(c)
            
        content = "\n".join(output)
        with open("sub.txt", "w") as f: f.write(base64.b64encode(content.encode()).decode())
        with open("sub_raw.txt", "w") as f: f.write(content)
        print(f"✨ Done! Found {len(output)} active configs.")
    
    await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())

import os
import re
import base64
import asyncio
import aiohttp
import random
from datetime import datetime
from zoneinfo import ZoneInfo
import jdatetime
from urllib.parse import urlparse, unquote, quote, urlunparse
from telethon import TelegramClient
from telethon.sessions import StringSession

# --- تنظیمات ---
CHANNELS = ['napsternetv', 'FreakConfig', 'Configir98']
SEARCH_LIMIT = 500 
MAX_TO_TEST = 60 # تعداد کانفیگ‌هایی که برای تست به check-host می‌فرستیم (برای جلوگیری از بلاک شدن)
FINAL_COUNT = 30 # تعداد نهایی که در ساب‌لینک ذخیره می‌شود

def get_persian_time():
    try:
        tehran_tz = ZoneInfo("Asia/Tehran")
        now_tehran = datetime.now(tehran_tz)
        return jdatetime.datetime.fromgregorian(datetime=now_tehran).strftime("%Y-%m-%d %H:%M")
    except: return datetime.now().strftime("%Y-%m-%d %H:%M")

def add_name_to_config(conf, time_tag):
    if conf.startswith("vmess://"): return conf
    try:
        parsed = urlparse(conf)
        name = f"IR_OK | {time_tag}"
        return urlunparse(parsed._replace(fragment=quote(name)))
    except: return conf

# --- بخش اصلی تست ایران ---
async def check_iran_node(session, config_url):
    """تست واقعی اتصال از نود تهران"""
    try:
        parsed = urlparse(config_url)
        host = parsed.hostname
        port = parsed.port if parsed.port else 443
        
        # ۱. ثبت درخواست در check-host
        api_url = f"https://check-host.net/check-tcp?host={host}:{port}&node=ir1.node.check-host.net"
        async with session.get(api_url, headers={'Accept': 'application/json'}) as resp:
            data = await resp.json()
            request_id = data.get('request_id')
        
        if not request_id: return None

        # ۲. انتظار برای بررسی (۱۰ ثانیه استاندارد)
        await asyncio.sleep(12)

        # ۳. دریافت نتیجه
        result_url = f"https://check-host.net/check-result/{request_id}"
        async with session.get(result_url) as resp:
            res_data = await resp.json()
            # بررسی اینکه آیا اتصال در نود ایران موفقیت‌آمیز بوده (مقدار ۱ یعنی وصل شد)
            ir_res = res_data.get('ir1.node.check-host.net')
            if ir_res and ir_res[0] is not None:
                print(f"✅ OK: {host}")
                return config_url
    except: pass
    return None

async def main():
    API_ID = int(os.environ.get("API_ID", 34146126))
    API_HASH = os.environ.get("API_HASH", "6f3350e049ef37676b729241f5bc8c5e")
    SESSION_STRING = os.environ.get("SESSION_STRING")
    if not SESSION_STRING: return

    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    
    try:
        await client.connect()
        all_configs = []
        
        # ۱. جمع‌آوری
        for channel in CHANNELS:
            print(f"📡 Scanning {channel}...")
            async for message in client.iter_messages(channel, limit=SEARCH_LIMIT):
                if message.text:
                    links = re.findall(r'(?:vmess|vless|ss|trojan|tuic|hysteria2?)://[^\s\t\n]+', message.text)
                    for conf in links:
                        c = re.split(r'[\s\n]+', conf)[0].strip().rstrip(')]}"\'>,')
                        all_configs.append(c)

        unique_configs = list(dict.fromkeys(all_configs))
        random.shuffle(unique_configs)
        configs_to_test = unique_configs[:MAX_TO_TEST]

        # ۲. تست موازی ایران
        print(f"🔍 Testing {len(configs_to_test)} configs via Iran Node...")
        async with aiohttp.ClientSession() as session:
            tasks = [check_iran_node(session, c) for c in configs_to_test]
            results = await asyncio.gather(*tasks)
        
        valid_configs = [r for r in results if r is not None][:FINAL_COUNT]
        
        # ۳. ذخیره‌سازی
        if valid_configs:
            time_tag = get_persian_time()
            final_list = [add_name_to_config(c, time_tag) for c in valid_configs]
            content = "\n".join(final_list)
            
            with open("sub.txt", "w") as f:
                f.write(base64.b64encode(content.encode()).decode())
            with open("sub_raw.txt", "w") as f:
                f.write(content)
            print(f"✨ Finished! {len(final_list)} configs are working in Iran.")
            
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())

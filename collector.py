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
CHANNELS = ['napsternetv', 'FreakConfig', 'Configir98', 'V2rayNGn', 'free_v2rayyy'] # کانال های بیشتر برای شانس بیشتر
SEARCH_LIMIT = 200 
MAX_TO_TEST = 50 # تعداد تست
FINAL_COUNT = 20
CONCURRENT_REQUESTS = 5 # حداکثر تعداد تست همزمان (برای جلوگیری از بن شدن توسط چک‌هاست)

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
        name = f"IR_Green | {time_tag}"
        return urlunparse(parsed._replace(fragment=quote(name)))
    except: return conf

# --- بخش تمیزکاری لینک ---
def clean_config(conf):
    # حذف کاراکترهای اضافی ته لینک که معمولا در تلگرام می‌چسبند
    return re.split(r'[ \n\t\r\)]', conf)[0]

# --- بخش اصلی تست ایران ---
async def check_iran_node(session, config_url, semaphore):
    async with semaphore: # محدود کردن تعداد درخواست‌های همزمان
        try:
            parsed = urlparse(config_url)
            host = parsed.hostname
            port = parsed.port if parsed.port else 443
            
            if not host: return None

            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

            # ۱. ثبت درخواست
            api_url = f"https://check-host.net/check-tcp?host={host}:{port}&node=ir1.node.check-host.net"
            async with session.get(api_url, headers=headers, timeout=10) as resp:
                if resp.status != 200:
                    return None
                data = await resp.json()
                request_id = data.get('request_id')
            
            if not request_id: return None

            # ۲. تاخیر هوشمند (کمی صبر کنید تا سرور پردازش کند)
            await asyncio.sleep(10)

            # ۳. دریافت نتیجه
            result_url = f"https://check-host.net/check-result/{request_id}"
            async with session.get(result_url, headers=headers, timeout=10) as resp:
                res_data = await resp.json()
                
                # لاجیک بررسی نتیجه
                ir_res = res_data.get('ir1.node.check-host.net')
                
                if not ir_res:
                    return None
                
                # بررسی اینکه آیا حداقل یک پکت موفق بوده یا اتصال برقرار شده
                # فرمت خروجی چک هاست: [{"time": 0.1, "address": "..."}] یا [{"error": "..."}]
                if isinstance(ir_res, list) and len(ir_res) > 0:
                    payload = ir_res[0]
                    if payload and isinstance(payload, dict):
                        if "time" in payload or "connected" in payload: # اگر تایم داد یعنی وصل شد
                            print(f"✅ Active: {host}")
                            return config_url
                        
        except Exception as e:
            # print(f"Error checking {config_url}: {e}") # برای دیباگ می‌توانید این خط را فعال کنید
            pass
        return None

async def main():
    API_ID = int(os.environ.get("API_ID", 34146126))
    API_HASH = os.environ.get("API_HASH", "6f3350e049ef37676b729241f5bc8c5e")
    SESSION_STRING = os.environ.get("SESSION_STRING")
    if not SESSION_STRING: 
        print("Error: SESSION_STRING not found")
        return

    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    
    try:
        await client.connect()
        all_configs = []
        
        # ۱. جمع‌آوری
        print("📥 Starting Scraping...")
        for channel in CHANNELS:
            try:
                print(f"   -> Scanning {channel}...")
                async for message in client.iter_messages(channel, limit=SEARCH_LIMIT):
                    if message.text:
                        # ریجکس بهبود یافته
                        links = re.findall(r'(?:vmess|vless|ss|trojan|tuic|hysteria2?)://[a-zA-Z0-9\-\._~:/\?#\[\]@!$&\'\(\)\*\+,;=%]+', message.text)
                        for conf in links:
                            clean = clean_config(conf)
                            if "127.0.0.1" not in clean and "localhost" not in clean: # حذف لوکال‌ها
                                all_configs.append(clean)
            except Exception as e:
                print(f"Error scraping {channel}: {e}")

        unique_configs = list(dict.fromkeys(all_configs))
        print(f"📊 Total Found: {len(unique_configs)}")

        if len(unique_configs) == 0:
            print("❌ No configs found!")
            return

        random.shuffle(unique_configs)
        configs_to_test = unique_configs[:MAX_TO_TEST]

        # ۲. تست موازی اما کنترل شده
        print(f"🔍 Testing {len(configs_to_test)} configs (Batch size: {CONCURRENT_REQUESTS})...")
        
        semaphore = asyncio.Semaphore(CONCURRENT_REQUESTS) # کنترل ترافیک
        async with aiohttp.ClientSession() as session:
            tasks = [check_iran_node(session, c, semaphore) for c in configs_to_test]
            results = await asyncio.gather(*tasks)
        
        valid_configs = [r for r in results if r is not None]
        
        # ۳. ذخیره‌سازی
        print(f"🎉 Working Configs: {len(valid_configs)}")
        
        if valid_configs:
            # محدود کردن تعداد نهایی
            final_selection = valid_configs[:FINAL_COUNT]
            time_tag = get_persian_time()
            final_list = [add_name_to_config(c, time_tag) for c in final_selection]
            content = "\n".join(final_list)
            
            with open("sub.txt", "w") as f:
                f.write(base64.b64encode(content.encode()).decode())
            with open("sub_raw.txt", "w") as f:
                f.write(content)
            print("💾 Saved to file.")
        else:
            print("⚠️ No working configs found in this run.")
            # ایجاد فایل خالی یا نگه داشتن قبلی (اینجا فایل خالی ساخته می‌شود تا ارور ندهد)
            with open("sub.txt", "w") as f: f.write("")
            with open("sub_raw.txt", "w") as f: f.write("")

    except Exception as e:
        print(f"Critical Error: {e}")
    finally:
        if client.is_connected():
            await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())

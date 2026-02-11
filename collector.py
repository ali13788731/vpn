import os
import re
import json
import base64
import asyncio
import random
from datetime import datetime
from zoneinfo import ZoneInfo
import jdatetime
from telethon import TelegramClient
from telethon.sessions import StringSession

# --- تنظیمات امنیتی (از Secrets خوانده می‌شود) ---

API_ID = 34146126
API_HASH = os.environ.get("API_HASH", "6f3350e049ef37676b729241f5bc8c5e")
SESSION_STRING = os.environ.get("SESSION_STRING")

CHANNELS = ['napsternetv']
SEARCH_LIMIT = 300
TOTAL_FINAL_COUNT = 100

# --- توابع کمکی ---

def get_persian_time():
    """دریافت زمان فعلی تهران به صورت شمسی"""
    try:
        tehran_tz = ZoneInfo("Asia/Tehran")
        now = datetime.now(tehran_tz)
        j_date = jdatetime.datetime.fromgregorian(datetime=now, locale='en_US')
        return j_date.strftime("%Y/%m/%d %H:%M")
    except:
        return datetime.now().strftime("%Y-%m-%d %H:%M")

async def check_connection(host, port, timeout=2):
    """تست سریع زنده بودن سرور به صورت Async"""
    try:
        conn = asyncio.open_connection(host, int(port))
        _, writer = await asyncio.wait_for(conn, timeout=timeout)
        writer.close()
        await writer.wait_closed()
        return True
    except:
        return False

def extract_host_port(config):
    """استخراج هاست و پورت برای حذف تکراری‌های واقعی"""
    try:
        if config.startswith("vmess://"):
            data = json.loads(base64.b64decode(config[8:]).decode('utf-8'))
            return f"{data.get('add')}:{data.get('port')}"
        else:
            match = re.search(r'@([^:/]+):(\d+)', config)
            if match:
                return f"{match.group(1)}:{match.group(2)}"
    except:
        pass
    return config # اگر پیدا نشد خود لینک را برگردان

def rename_config(config, new_name):
    """تغییر نام هوشمند برای انواع پروتکل‌ها (حتی Vmess)"""
    try:
        if config.startswith("vmess://"):
            data_b64 = config[8:]
            data = json.loads(base64.b64decode(data_b64).decode('utf-8'))
            data['ps'] = new_name
            return "vmess://" + base64.b64encode(json.dumps(data).encode('utf-8')).decode('utf-8')
        elif "#" in config:
            return config.split("#")[0] + "#" + new_name
        else:
            return config + "#" + new_name
    except:
        return config

# --- بدنه اصلی اسکریپت ---

async def main():
    if not SESSION_STRING or API_ID == 0:
        print("❌ تنظیمات API_ID یا SESSION_STRING یافت نشد!")
        return

    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

    try:
        await client.connect()
        print("🚀 در حال استخراج کانفیگ‌ها...")
        
        raw_links = []
        time_tag = get_persian_time()

        for channel in CHANNELS:
            print(f"📡 اسکن @{channel}...")
            async for message in client.iter_messages(channel, limit=SEARCH_LIMIT):
                if message.text:
                    found = re.findall(r'(?:vmess|vless|ss|trojan|tuic|hysteria2?)://\S+', message.text)
                    for link in found:
                        # تمیزکاری اولیه
                        link = link.strip().split('\n')[0].split('<')[0].split('"')[0]
                        link = re.sub(r'[)\]}"\'>]+$', '', link)
                        raw_links.append(link)

        # ۱. حذف تکراری‌های بر اساس آدرس سرور
        unique_configs = {}
        for link in raw_links:
            server_identity = extract_host_port(link)
            if server_identity not in unique_configs:
                unique_configs[server_identity] = link

        print(f"🔍 تعداد کل منحصربه‌فرد: {len(unique_configs)}")

        # ۲. تست پینگ همزمان (Async)
        tasks = []
        candidates = list(unique_configs.values())
        
        print("⚡ در حال تست پینگ سرورها...")
        for conf in candidates:
            identity = extract_host_port(conf)
            if ":" in identity:
                host, port = identity.split(":")
                tasks.append(check_connection(host, port))
            else:
                tasks.append(asyncio.sleep(0, result=False)) # لینک نامعتبر

        results = await asyncio.gather(*tasks)
        
        valid_configs = []
        for i, is_alive in enumerate(results):
            if is_alive:
                conf = candidates[i]
                # ۳. تغییر نام با تاریخ شمسی و ایموجی
                proto = conf.split("://")[0].upper()
                new_name = f"🚀 {proto} | {time_tag} | @Sub"
                final_conf = rename_config(conf, new_name)
                valid_configs.append(final_conf)
                
            if len(valid_configs) >= TOTAL_FINAL_COUNT:
                break

        # ۴. ذخیره‌سازی نهایی
        if valid_configs:
            content = "\n".join(valid_configs)
            encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
            with open("sub.txt", "w") as f:
                f.write(encoded)
            print(f"✅ {len(valid_configs)} کانفیگ سالم ذخیره شد.")
        else:
            print("⚠️ هیچ کانفیگ سالمی پیدا نشد.")

    except Exception as e:
        print(f"❌ خطای کلی: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())

import os
import re
import json
import base64
import asyncio
from datetime import datetime
from zoneinfo import ZoneInfo
import jdatetime
from telethon import TelegramClient
from telethon.sessions import StringSession

# --- تنظیمات امنیتی (از Secrets خوانده می‌شود) ---
API_ID = int(os.environ.get("API_ID", 0))
API_HASH = os.environ.get("API_HASH", "")
SESSION_STRING = os.environ.get("SESSION_STRING", "")

CHANNELS = ['napsternetv']
SEARCH_LIMIT = 300
TOTAL_FINAL_COUNT = 100

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
    """تست سریع زنده بودن سرور"""
    try:
        conn = asyncio.open_connection(host, int(port))
        _, writer = await asyncio.wait_for(conn, timeout=timeout)
        writer.close()
        await writer.wait_closed()
        return True
    except:
        return False

def extract_host_port(config):
    """استخراج هاست و پورت برای شناسایی تکراری‌ها"""
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
    return config

def rename_config(config, new_name):
    """تغییر نام هوشمند پروتکل‌ها"""
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

async def main():
    if not SESSION_STRING or API_ID == 0:
        print("❌ Error: API_ID or SESSION_STRING is missing!")
        return

    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)

    try:
        await client.connect()
        print("🚀 Starting extraction...")
        
        raw_links = []
        time_tag = get_persian_time()

        for channel in CHANNELS:
            print(f"📡 Scanning @{channel}...")
            async for message in client.iter_messages(channel, limit=SEARCH_LIMIT):
                if message.text:
                    found = re.findall(r'(?:vmess|vless|ss|trojan|tuic|hysteria2?)://\S+', message.text)
                    for link in found:
                        link = re.sub(r'[)\]}"\'>]+$', '', link.strip().split('\n')[0])
                        raw_links.append(link)

        unique_configs = {}
        for link in raw_links:
            server_identity = extract_host_port(link)
            if server_identity not in unique_configs:
                unique_configs[server_identity] = link

        print(f"🔍 Unique configs found: {len(unique_configs)}")

        tasks = []
        candidates = list(unique_configs.values())
        for conf in candidates:
            identity = extract_host_port(conf)
            if ":" in identity:
                host, port = identity.split(":")
                tasks.append(check_connection(host, port))
            else:
                tasks.append(asyncio.sleep(0, result=False))

        results = await asyncio.gather(*tasks)
        
        valid_configs = []
        for i, is_alive in enumerate(results):
            if is_alive:
                conf = candidates[i]
                proto = conf.split("://")[0].upper()
                new_name = f"🚀 {proto} | {time_tag} | @Sub"
                valid_configs.append(rename_config(conf, new_name))
            
            if len(valid_configs) >= TOTAL_FINAL_COUNT:
                break

        if valid_configs:
            content = "\n".join(valid_configs)
            encoded = base64.b64encode(content.encode('utf-8')).decode('utf-8')
            with open("sub.txt", "w") as f:
                f.write(encoded)
            print(f"✅ Saved {len(valid_configs)} active configs to sub.txt")
        else:
            print("⚠️ No active configs found.")

    except Exception as e:
        print(f"❌ General Error: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())

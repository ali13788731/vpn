import os
import re
import base64
import asyncio
import socket
import random
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.network import ConnectionTcpFull

# تنظیمات
API_ID = 34146126  
API_HASH = os.environ.get("API_HASH", "6f3350e049ef37676b729241f5bc8c5e")
SESSION_STRING = os.environ.get("SESSION_STRING")

# لیست کانال‌های هدف
CHANNELS = [
    'napsternetv'
]

SEARCH_LIMIT = 500 
TOTAL_FINAL_COUNT = 100

def is_server_alive(host, port):
    try:
        socket.setdefaulttimeout(1)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, int(port)))
        return True
    except:
        return False

async def main():
    if not SESSION_STRING:
        print("❌ SESSION_STRING Found!")
        return

    client = TelegramClient(
        StringSession(SESSION_STRING), 
        API_ID, 
        API_HASH,
        connection=ConnectionTcpFull
    )
    
    try:
        await client.connect()
        if not await client.is_user_authorized():
            print("❌ سشن نامعتبر است!")
            return

        print("🚀 در حال جمع‌آوری کانفیگ‌ها...")
        all_raw_configs = []
        
        for channel in CHANNELS:
            print(f"📡 اسکن @{channel}...")
            try:
                async for message in client.iter_messages(channel, limit=SEARCH_LIMIT):
                    if message.text:
                        pattern = r'(vmess://[a-zA-Z0-9+/=]+|vless://[a-zA-Z0-9\-@:?=&%.]+|ss://[a-zA-Z0-9\-@:?=&%.]+|trojan://[a-zA-Z0-9\-@:?=&%.]+)'
                        found = re.findall(pattern, message.text)
                        all_raw_configs.extend(found)
                await asyncio.sleep(random.randint(1, 3)) 
            except Exception as e:
                print(f"⚠️ خطا در کانال {channel}: {e}")
                continue

        unique_configs = list(dict.fromkeys(all_raw_configs))
        valid_configs = []

        for conf in unique_configs:
            if len(valid_configs) >= TOTAL_FINAL_COUNT: break
            try:
                if "@" in conf:
                    parts = re.search(r'@([^:]+):(\d+)', conf)
                    if parts and is_server_alive(parts.group(1), parts.group(2)):
                        valid_configs.append(conf)
                else:
                    valid_configs.append(conf)
            except:
                continue

        if valid_configs:
            content_str = "\n".join(valid_configs)
            encoded = base64.b64encode(content_str.encode('utf-8')).decode('utf-8')
            with open("sub.txt", "w") as f:
                f.write(encoded)
            print(f"✨ {len(valid_configs)} کانفیگ با موفقیت ذخیره شد.")
        else:
            print("⚠️ کانفیگی پیدا نشد.")

    except Exception as e:
        print(f"⚠️ Error: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())

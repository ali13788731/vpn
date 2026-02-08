import os
import re
import base64
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.network import ConnectionTcpFull

# تنظیمات
API_ID = 34146126  
API_HASH = os.environ.get("API_HASH", "6f3350e049ef37676b729241f5bc8c5e")
SESSION_STRING = os.environ.get("SESSION_STRING")
TARGET_CHANNEL = 'napsternetv' 
SEARCH_LIMIT = 200 
FINAL_COUNT = 50

async def main():
    if not SESSION_STRING:
        print("❌ SESSION_STRING یافت نشد!")
        return

    client = TelegramClient(
        StringSession(SESSION_STRING), 
        API_ID, 
        API_HASH,
        connection=ConnectionTcpFull,
        connection_retries=20,
        retry_delay=10,
        timeout=60
    )
    
    try:
        await client.connect()
        if not await client.is_user_authorized():
            print("❌ سشن نامعتبر است!")
            return

        print(f"✅ اسکن کانال @{TARGET_CHANNEL}...")
        configs = []
        async for message in client.iter_messages(TARGET_CHANNEL, limit=SEARCH_LIMIT):
            if message.text:
                pattern = r'(vmess://[a-zA-Z0-9+/=]+|vless://[a-zA-Z0-9\-@:?=&%.]+|ss://[a-zA-Z0-9\-@:?=&%.]+|trojan://[a-zA-Z0-9\-@:?=&%.]+)'
                found = re.findall(pattern, message.text)
                if found:
                    configs.extend(found)

        unique_configs = list(dict.fromkeys(configs))
        final_list = unique_configs[:FINAL_COUNT]
        
        if final_list:
            content_str = "\n".join(final_list)
            encoded_content = base64.b64encode(content_str.encode('utf-8')).decode('utf-8')
            with open("sub.txt", "w") as f:
                f.write(encoded_content)
            print(f"✔️ {len(final_list)} کانفیگ ذخیره شد.")
        else:
            print("⚠️ چیزی پیدا نشد.")
    except Exception as e:
        print(f"⚠️ خطا: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())

import os
import json
import asyncio
from telethon import TelegramClient
from telethon.sessions import StringSession

api_id = int(os.environ.get("API_ID", 34146126))
api_hash = os.environ.get("API_HASH", "6f3350e049ef37676b729241f5bc8c5e")
session_string = os.environ.get("SESSION_STRING")
target_channel = os.environ.get("TARGET_CHANNEL", "napsternetv")

async def main():
    if not session_string:
        print("❌ SESSION_STRING Not Found!")
        return

    client = TelegramClient(StringSession(session_string), api_id, api_hash)
    
    try:
        await client.connect()
        messages_data = []
        
        print(f"📡 Fetching last 100 messages from @{target_channel}...")
        async for msg in client.iter_messages(target_channel, limit=100):
            if msg.text:
                messages_data.append({
                    "id": msg.id,
                    "date": msg.date.strftime("%Y-%m-%d %H:%M"),
                    "text": msg.text
                })
        
        with open("messages.json", "w", encoding="utf-8") as f:
            json.dump(messages_data, f, ensure_ascii=False, indent=4)
        
        print(f"✅ Saved {len(messages_data)} messages.")

    except Exception as e:
        print(f"⚠️ Error: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())

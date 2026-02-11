import os
import re
import base64
import asyncio
import socket
import random
from datetime import datetime
from zoneinfo import ZoneInfo
import jdatetime  # کتابخانه جدید برای تاریخ شمسی
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.network import ConnectionTcpFull

# تنظیمات
API_ID = 34146126
API_HASH = os.environ.get("API_HASH", "6f3350e049ef37676b729241f5bc8c5e")
SESSION_STRING = os.environ.get("SESSION_STRING")

CHANNELS = ['napsternetv']
SEARCH_LIMIT = 1000
TOTAL_FINAL_COUNT = 200

def get_persian_time():
    try:
        # گرفتن زمان دقیق تهران
        tehran_tz = ZoneInfo("Asia/Tehran")
        now_tehran = datetime.now(tehran_tz)
        
        # تبدیل به تاریخ شمسی
        # locale='en_US' باعث می‌شود اعداد انگلیسی درج شوند (1403 بجای ۱۴۰۳) که برای کانفیگ بهتر است
        j_date = jdatetime.datetime.fromgregorian(datetime=now_tehran, locale='en_US')
        
        return j_date.strftime("%Y-%m-%d %H:%M")
    except Exception as e:
        print(f"Error time: {e}")
        return "Unknown-Time"

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

        # دریافت زمان شمسی
        time_tag = get_persian_time()
        print(f"⏰ زمان فعلی تهران: {time_tag}")

        for channel in CHANNELS:
            print(f"📡 اسکن @{channel}...")
            try:
                async for message in client.iter_messages(channel, limit=SEARCH_LIMIT):
                    if message.text:
                        links = re.findall(r'(?:vmess|vless|ss|trojan|tuic|hysteria2?)://\S+', message.text)

                        for conf in links:
                            conf = conf.strip().split('\n')[0]
                            conf = re.sub(r'[)\]}"\'>]+$', '', conf)
                            
                            # نادیده گرفتن Vmess برای تغییر نام (چون لینک خراب می‌شود)
                            if not conf.startswith("vmess://"):
                                # اگر هشتگ (#) دارد، به انتهایش اضافه کن
                                if "#" in conf:
                                    if time_tag not in conf:
                                        conf = f"{conf} | {time_tag}"
                                else:
                                    # اگر ندارد، بساز
                                    conf = f"{conf}#{time_tag}"
                            
                            all_raw_configs.append(conf)
                
                await asyncio.sleep(random.randint(1, 2))
            except Exception as e:
                print(f"⚠️ خطا در کانال {channel}: {e}")

        unique_configs = list(dict.fromkeys(all_raw_configs))
        valid_configs = unique_configs[:TOTAL_FINAL_COUNT]

        if valid_configs:
            content_str = "\n".join(valid_configs)
            encoded = base64.b64encode(content_str.encode('utf-8')).decode('utf-8')
            with open("sub.txt", "w") as f:
                f.write(encoded)
            print(f"✨ {len(valid_configs)} کانفیگ با تاریخ شمسی ذخیره شد.")
        else:
            print("⚠️ کانفیگی پیدا نشد.")

    except Exception as e:
        print(f"⚠️ Error: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())

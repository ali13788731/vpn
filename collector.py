import os
import re
import base64
import asyncio
import socket
import random
from datetime import datetime
import pytz 
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.network import ConnectionTcpFull

# تنظیمات
API_ID = 34146126
API_HASH = os.environ.get("API_HASH", "6f3350e049ef37676b729241f5bc8c5e")
SESSION_STRING = os.environ.get("SESSION_STRING")

# لیست کانال‌های اصلاح شده (این‌ها متن خام می‌ذارن)
CHANNELS = [
    'napsternetv'
] 

SEARCH_LIMIT = 200 # تعداد کمتر ولی از کانال‌های بیشتر اسکن می‌کنیم
TARGET_COUNT = random.randint(80, 100)

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
        print("⏳ در حال اتصال به تلگرام...")
        await client.connect()
        if not await client.is_user_authorized():
            print("❌ سشن نامعتبر است!")
            return

        print(f"🚀 هدف: جمع‌آوری {TARGET_COUNT} کانفیگ از {len(CHANNELS)} کانال...")
        all_raw_configs = []

        for channel in CHANNELS:
            if len(all_raw_configs) >= TARGET_COUNT:
                break
                
            print(f"📡 اسکن @{channel}...")
            try:
                # تلاش برای پیدا کردن کانال
                try:
                    entity = await client.get_entity(channel)
                except:
                    print(f"⚠️ کانال {channel} پیدا نشد، رد کردن...")
                    continue

                async for message in client.iter_messages(entity, limit=SEARCH_LIMIT):
                    if len(all_raw_configs) >= TARGET_COUNT:
                        break
                        
                    if message.text:
                        # پترن اصلاح شده: اضافه شدن ss (Shadowsocks) و flag=re.IGNORECASE برای حروف بزرگ
                        # همچنین حذف کاراکترهای مزاحم انتهای لینک
                        pattern = r'(vmess|vless|trojan|tuic|hysteria2?|ss|ssr)://[a-zA-Z0-9\-\_\=\:\@\.\?\&\%\#]+'
                        
                        links = re.findall(pattern, message.text, re.IGNORECASE)

                        if links:
                            # انتخاب رندوم از پیام برای تنوع بیشتر
                            selected_conf = random.choice(links)
                            
                            # تمیزکاری نهایی
                            selected_conf = selected_conf.strip()
                            
                            # اگر اسم نداشت، براش اسم می‌ذاریم
                            if "#" not in selected_conf:
                                selected_conf = f"{selected_conf}#Ali_Config_{random.randint(100, 999)}"
                            
                            all_raw_configs.append(selected_conf)
                
                print(f"✅ تا الان: {len(all_raw_configs)} کانفیگ جمع شد.")
                
            except Exception as e:
                print(f"⚠️ خطا در اسکن {channel}: {e}")

        # حذف تکراری‌ها
        unique_configs = list(dict.fromkeys(all_raw_configs))
        final_configs = unique_configs[:TARGET_COUNT]
        
        print(f"🔍 تعداد نهایی (بدون تکرار): {len(final_configs)}")

        if final_configs:
            # تنظیم زمان آپدیت
            try:
                # تلاش برای گرفتن زمان تهران
                tehran_tz = pytz.timezone('Asia/Tehran')
                now = datetime.now(tehran_tz)
            except:
                now = datetime.now()
                
            date_str = now.strftime("%H:%M - %Y/%m/%d")
            
            # هدر نمایشی
            header_conf = f"vless://00000000-0000-0000-0000-000000000000@127.0.0.1:443?encryption=none&security=none&type=tcp&headerType=none#Updated: {date_str}"
            
            final_configs.insert(0, header_conf)
            final_configs.insert(1, f"vless://00000000-0000-0000-0000-000000000000@127.0.0.1:443?encryption=none&security=none&type=tcp&headerType=none#Count: {len(final_configs)-2}")

            content_str = "\n".join(final_configs)
            
            # انکدینگ نهایی (برای برخی کلاینت‌ها بهتره که نباشه، ولی طبق کد خودت گذاشتم)
            # اگر خواستی ساده باشه، خط زیر رو کامنت کن و content_str رو مستقیم بنویس
            encoded = base64.b64encode(content_str.encode('utf-8')).decode('utf-8')
            
            with open("sub.txt", "w") as f:
                f.write(encoded) # یا content_str
            print("✨ فایل sub.txt با موفقیت ذخیره شد.")
        else:
            print("⚠️ هیچ کانفیگی پیدا نشد! (شاید کانال‌ها فیلترن یا سشن مشکل داره)")

    except Exception as e:
        print(f"⚠️ Critical Error: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())

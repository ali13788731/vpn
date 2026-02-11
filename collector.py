import os
import re
import base64
import asyncio
import socket
import random
from datetime import datetime
import pytz # اگر نصب نیست باید به requirements اضافه بشه یا از روش ساده‌تر استفاده کنیم
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.network import ConnectionTcpFull

# تنظیمات
API_ID = 34146126
API_HASH = os.environ.get("API_HASH", "6f3350e049ef37676b729241f5bc8c5e")
SESSION_STRING = os.environ.get("SESSION_STRING")

CHANNELS = ['napsternetv'] # کانال‌های بیشتر اضافه کن تا زودتر پر بشه
SEARCH_LIMIT = 1000  # افزایش دادم تا چون از هر پیام یکی برمیداریم، کم نیاد
# عدد نهایی اینجا محاسبه میشه (بین 80 تا 100)
TARGET_COUNT = random.randint(80, 100)

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

        print(f"🚀 هدف: جمع‌آوری {TARGET_COUNT} کانفیگ (رندوم)...")
        all_raw_configs = []

        for channel in CHANNELS:
            if len(all_raw_configs) >= TARGET_COUNT:
                break
                
            print(f"📡 اسکن @{channel}...")
            try:
                async for message in client.iter_messages(channel, limit=SEARCH_LIMIT):
                    if len(all_raw_configs) >= TARGET_COUNT:
                        break
                        
                    if message.text:
                        # حذف ss از پترن
                        pattern = r'(vmess|vless|trojan|tuic|hysteria2?)://\S+'
                        # پیدا کردن همه لینک‌ها
                        links = re.findall(pattern, message.text)

                        # --- تغییر مهم: فقط برداشتن اولین کانفیگ از پیام ---
                        if links:
                            # فقط اولین لینک پیدا شده در پیام را بردار (links[0])
                            # اگر میخواهی کاملا رندوم باشه از پیام: random.choice(links)
                            selected_conf = links[0] 
                            
                            # تمیزکاری لینک
                            selected_conf = selected_conf.strip().split('\n')[0]
                            selected_conf = re.sub(r'[)\]}"\'>]+$', '', selected_conf)

                            # مدیریت نام (Remark)
                            if not selected_conf.startswith("vmess://"):
                                if "#" not in selected_conf:
                                    selected_conf = f"{selected_conf}#Config_{random.randint(10, 99)}"
                            
                            all_raw_configs.append(selected_conf)
                
                await asyncio.sleep(1)
            except Exception as e:
                print(f"⚠️ خطا در کانال {channel}: {e}")

        # حذف تکراری‌ها (هرچند با منطق بالا احتمال تکرار کمه ولی لازمه)
        unique_configs = list(dict.fromkeys(all_raw_configs))
        
        # اگر بعد از حذف تکراری‌ها کمتر از حد مجاز بود، و هنوز جا داشتیم، مشکلی نیست
        # اگر بیشتر بود، کات می‌کنیم تا دقیقا همون عدد رندوم بشه
        final_configs = unique_configs[:TARGET_COUNT]
        
        print(f"🔍 تعداد نهایی آماده شده: {len(final_configs)}")

        if final_configs:
            # --- اضافه کردن تاریخ آپدیت به عنوان اولین آیتم ---
            # دریافت زمان به وقت ایران (یا جهانی)
            now = datetime.now()
            date_str = now.strftime("%H:%M - %Y/%m/%d")
            
            # ساخت یک کانفیگ فیک که فقط نقش نمایش تاریخ رو داره (معمولا کلاینت‌ها اینو نشون میدن)
            # از پروتکل vless استفاده میکنیم چون راحت‌تر اسم رو نشون میده
            header_conf = f"vless://uuid@1.1.1.1:443?encryption=none&security=none&type=tcp&headerType=none#Updated: {date_str}"
            
            # گذاشتن تاریخ اول لیست
            final_configs.insert(0, header_conf)

            content_str = "\n".join(final_configs)
            encoded = base64.b64encode(content_str.encode('utf-8')).decode('utf-8')
            
            with open("sub.txt", "w") as f:
                f.write(encoded)
            print(f"✨ فایل ذخیره شد. (شامل {len(final_configs)-1} کانفیگ واقعی + زمان آپدیت)")
        else:
            print("⚠️ کانفیگی پیدا نشد.")

    except Exception as e:
        print(f"⚠️ Error: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())

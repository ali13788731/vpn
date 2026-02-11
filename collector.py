import os
import re
import base64
import asyncio
import socket
import random
from datetime import datetime
from zoneinfo import ZoneInfo  # پایتون 3.9+
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.network import ConnectionTcpFull

# تنظیمات
API_ID = 34146126
API_HASH = os.environ.get("API_HASH", "6f3350e049ef37676b729241f5bc8c5e")
SESSION_STRING = os.environ.get("SESSION_STRING")

CHANNELS = ['napsternetv']
SEARCH_LIMIT = 300
TOTAL_FINAL_COUNT = 100

def is_server_alive(host, port):
    try:
        socket.setdefaulttimeout(1)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.connect((host, int(port)))
        return True
    except:
        return False

# تابع برای گرفتن زمان تهران
def get_tehran_time():
    try:
        tehran_tz = ZoneInfo("Asia/Tehran")
        now = datetime.now(tehran_tz)
        # فرمت خروجی: 2024-05-20 14:30
        return now.strftime("%Y-%m-%d %H:%M")
    except Exception:
        # اگر مشکلی در تایم‌زون بود، ساعت جهانی را می‌گیرد
        return datetime.now().strftime("%Y-%m-%d %H:%M")

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

        # دریافت زمان فعلی برای استفاده در نام کانفیگ‌ها
        time_tag = get_tehran_time()

        for channel in CHANNELS:
            print(f"📡 اسکن @{channel}...")
            try:
                async for message in client.iter_messages(channel, limit=SEARCH_LIMIT):
                    if message.text:
                        links = re.findall(r'(?:vmess|vless|ss|trojan|tuic|hysteria2?)://\S+', message.text)

                        for conf in links:
                            # تمیز کردن کاراکترهای اضافه
                            conf = conf.strip().split('\n')[0]
                            conf = re.sub(r'[)\]}"\'>]+$', '', conf)
                            
                            # --- اصلاح نام و افزودن تاریخ ---
                            # نکته: vmess ساختار JSON Base64 دارد و تغییر نام آن پیچیده است و معمولا تغییر داده نمی‌شود
                            # اما برای بقیه پروتکل‌ها (vless, trojan, ss, etc) نام بعد از # قرار می‌گیرد.
                            
                            if not conf.startswith("vmess://"):
                                # بررسی وجود علامت # (Remark)
                                if "#" in conf:
                                    # اگر نام دارد، تاریخ را به انتهای آن اضافه کن
                                    # مثال: vless://...@...?#ExistingName | 2024-01-01 12:00
                                    if f"| {time_tag}" not in conf: # جلوگیری از تکرار اگر قبلا اضافه شده
                                        conf = f"{conf} | {time_tag}"
                                else:
                                    # اگر نام ندارد، یک نام جدید با تاریخ بساز
                                    conf = f"{conf}#Network_{random.randint(10,99)}_{time_tag}"
                            
                            all_raw_configs.append(conf)
                
                await asyncio.sleep(random.randint(1, 2))
            except Exception as e:
                print(f"⚠️ خطا در کانال {channel}: {e}")

        unique_configs = list(dict.fromkeys(all_raw_configs))
        valid_configs = []
        print(f"🔍 تعداد کل پیدا شده: {len(unique_configs)}")

        for conf in unique_configs:
            if len(valid_configs) >= TOTAL_FINAL_COUNT:
                break
            
            # افزودن بدون تست پینگ (برای سرعت بیشتر طبق کد قبلی شما)
            valid_configs.append(conf)

        if valid_configs:
            content_str = "\n".join(valid_configs)
            encoded = base64.b64encode(content_str.encode('utf-8')).decode('utf-8')
            with open("sub.txt", "w") as f:
                f.write(encoded)
            print(f"✨ {len(valid_configs)} کانفیگ با تاریخ {time_tag} ذخیره شد.")
        else:
            print("⚠️ کانفیگی پیدا نشد.")

    except Exception as e:
        print(f"⚠️ Error: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())

import os
import re
import base64
import asyncio
import socket
import random
import jdatetime  # کتابخانه برای تاریخ شمسی
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.network import ConnectionTcpFull

# تنظیمات
API_ID = 34146126
API_HASH = os.environ.get("API_HASH", "6f3350e049ef37676b729241f5bc8c5e")
SESSION_STRING = os.environ.get("SESSION_STRING")

CHANNELS = ['napsternetv']
SEARCH_LIMIT = 700
TOTAL_FINAL_COUNT = 200

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

        # دریافت تاریخ و ساعت شمسی جاری برای کل این اجرا
        # فرمت: 1402-11-23_10:30
        current_fa_date = jdatetime.datetime.now().strftime("%Y-%m-%d_%H:%M")

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
                            
                            # --- بخش اصلاح شده برای اضافه کردن تاریخ شمسی ---
                            try:
                                # جدا کردن نام کانفیگ (اگر وجود داشته باشد) از بدنه لینک
                                if "#" in conf:
                                    # اگر قبلاً # دارد، تاریخ را به انتهای نام فعلی اضافه کن
                                    # برای جلوگیری از تکرار تاریخ اگر قبلاً اضافه شده باشد، چک نمی‌کنیم (ساده‌سازی)
                                    conf = f"{conf}_{current_fa_date}"
                                else:
                                    # اگر نام ندارد، یک نام تصادفی + تاریخ اضافه کن
                                    # نکته: برای vmess معمولا نام داخل json است اما اکثر کلاینت‌ها # را در انتها قبول می‌کنند
                                    conf = f"{conf}#Config_{random.randint(100, 999)}_{current_fa_date}"
                            except Exception as e:
                                # در صورت بروز خطا در تغییر نام، همان کانفیگ اصلی را نگه دار
                                pass
                            
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
            
            # اینجا فقط کانفیگ را اضافه می‌کنیم (بررسی پینگ اختیاری است و کامنت شده)
            valid_configs.append(conf)

        if valid_configs:
            content_str = "\n".join(valid_configs)
            encoded = base64.b64encode(content_str.encode('utf-8')).decode('utf-8')
            with open("sub.txt", "w") as f:
                f.write(encoded)
            print(f"✨ {len(valid_configs)} کانفیگ با تاریخ شمسی ({current_fa_date}) ذخیره شد.")
        else:
            print("⚠️ کانفیگی پیدا نشد.")

    except Exception as e:
        print(f"⚠️ Error: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())

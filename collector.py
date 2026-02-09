import os
import re
import base64
import asyncio
import random
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.network import ConnectionTcpFull

# تنظیمات
API_ID = int(os.environ.get("API_ID", 34146126))
API_HASH = os.environ.get("API_HASH", "6f3350e049ef37676b729241f5bc8c5e")
SESSION_STRING = os.environ.get("SESSION_STRING")

# لیست کانال‌های هدف
CHANNELS = [
    'napsternetv',
    'v2rayng_org',
    'v2ray_outlineir'
]

SEARCH_LIMIT = 200  # تعداد پیام برای بررسی در هر کانال
TOTAL_FINAL_COUNT = 500 # حداکثر تعداد کانفیگ نهایی

async def check_port(host, port, timeout=2):
    """
    تست اتصال غیرهمگام (Async) به پورت
    """
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, int(port)), timeout=timeout
        )
        writer.close()
        await writer.wait_closed()
        return True
    except:
        return False

def clean_config(conf):
    """
    پاکسازی کانفیگ از کاراکترهای اضافی و توضیحات فارسی/هشتگ
    """
    # حذف هشتگ و توضیحات بعد از آن (برای vless/vmess/trojan)
    # معمولاً کانفیگ‌ها تا قبل از کاراکتر # معتبر هستند (مگر اینکه اسم در انکدینگ باشد که بحثش جداست)
    # اما در لینک‌های استاندارد، فرگمنت (#) برای نامگذاری است و حذفش مشکلی در اتصال ایجاد نمی‌کند.
    conf = re.sub(r'#.*$', '', conf)
    
    # حذف کاراکترهای مارک‌داون یا HTML که ممکن است چسبیده باشند
    conf = re.sub(r'[)\]}"\'>]+$', '', conf)
    
    # حذف فاصله‌های خالی
    return conf.strip()

async def main():
    if not SESSION_STRING:
        print("❌ Error: SESSION_STRING not found in environment variables!")
        return

    client = TelegramClient(
        StringSession(SESSION_STRING), 
        API_ID, 
        API_HASH,
        connection=ConnectionTcpFull
    )
    
    try:
        print("🚀 Connecting to Telegram...")
        await client.connect()
        if not await client.is_user_authorized():
            print("❌ Error: Session is invalid or not authorized!")
            return

        print("📥 Starting config collection...")
        all_raw_configs = []
        
        # الگوی دقیق‌تر برای استخراج
        # این الگو سعی می‌کند پروتکل را بگیرد و تا رسیدن به فضای خالی یا خط بعد ادامه دهد
        pattern = r'(vmess://[a-zA-Z0-9+/=]+|vless://[^#\s]+|ss://[^#\s]+|trojan://[^#\s]+|tuic://[^#\s]+|hysteria2?://[^#\s]+)'

        for channel in CHANNELS:
            print(f"📡 Scanning: @{channel}")
            try:
                msg_count = 0
                async for message in client.iter_messages(channel, limit=SEARCH_LIMIT):
                    if message.text:
                        found = re.findall(pattern, message.text)
                        for conf in found:
                            cleaned = clean_config(conf)
                            if cleaned:
                                all_raw_configs.append(cleaned)
                    msg_count += 1
                print(f"   ✅ Scanned {msg_count} messages.")
            except Exception as e:
                print(f"   ⚠️ Error collecting from {channel}: {e}")

        # حذف تکراری‌ها
        unique_configs = list(dict.fromkeys(all_raw_configs))
        print(f"🔍 Total unique configs found: {len(unique_configs)}")

        valid_configs = []
        
        # Semaphore برای کنترل تعداد تست‌های همزمان (جلوگیری از کرش کردن به دلیل باز کردن سوکت زیاد)
        sem = asyncio.Semaphore(20) 

        async def validate(conf):
            if len(valid_configs) >= TOTAL_FINAL_COUNT:
                return

            # لاجیک استخراج آدرس و پورت
            host, port = None, None
            
            # استخراج برای VLESS, Trojan, SS (فرمت ساده)
            if "@" in conf and ":" in conf:
                try:
                    # تلاش برای پیدا کردن IP و Port بین @ و ? یا انتهای خط
                    match = re.search(r'@([^:/?#]+):(\d+)', conf)
                    if match:
                        host = match.group(1)
                        port = match.group(2)
                except:
                    pass
            
            # اگر هاست و پورت پیدا شد، تست کن
            if host and port:
                async with sem:
                    is_alive = await check_port(host, port)
                    if is_alive:
                        valid_configs.append(conf)
                        print(f"   🟢 Alive: {host}:{port}")
                    else:
                        # print(f"   🔴 Dead: {host}:{port}") # اختیاری: برای شلوغ نشدن لاگ کامنت شد
                        pass
            else:
                # برای VMess یا فرمت‌های پیچیده که پارس نکردیم، فعلاً اضافه می‌کنیم (یا می‌توانید حذف کنید)
                valid_configs.append(conf)

        # اجرای تست‌ها به صورت همزمان (Concurrent)
        print("⚡ Testing configs connectivity...")
        tasks = [validate(conf) for conf in unique_configs]
        await asyncio.gather(*tasks)

        # ذخیره خروجی
        if valid_configs:
            # محدود کردن به تعداد درخواستی
            final_list = valid_configs[:TOTAL_FINAL_COUNT]
            content_str = "\n".join(final_list)
            
            # انکد کردن به Base64 (فرمت Subscription)
            encoded = base64.b64encode(content_str.encode('utf-8')).decode('utf-8')
            
            with open("sub.txt", "w") as f:
                f.write(encoded)
            
            # ذخیره فایل بدون انکد (اختیاری - برای دیباگ)
            with open("sub_raw.txt", "w") as f:
                 f.write(content_str)

            print(f"✨ Success! Saved {len(final_list)} configs to sub.txt")
        else:
            print("⚠️ No valid configs found.")

    except Exception as e:
        print(f"⚠️ Critical Error: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())

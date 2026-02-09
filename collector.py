import os
import re
import base64
import json
import asyncio
import binascii
from urllib.parse import urlparse
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.network import ConnectionTcpFull

# پیشنهاد می‌شود اگر می‌توانید کتابخانه tqdm را نصب کنید: pip install tqdm
try:
    from tqdm.asyncio import tqdm
except ImportError:
    # یک جایگزین ساده اگر tqdm نصب نبود
    def tqdm(iterable, **kwargs):
        return iterable

# --- تنظیمات ---
API_ID = int(os.environ.get("API_ID", 34146126))
API_HASH = os.environ.get("API_HASH", "6f3350e049ef37676b729241f5bc8c5e")
SESSION_STRING = os.environ.get("SESSION_STRING")

CHANNELS = [
    'napsternetv',
    'v2rayng_org', # کانال‌های بیشتر برای تست
    'v2ray_outlineir',
]

SEARCH_LIMIT = 200
TOTAL_FINAL_COUNT = 500
TIMEOUT_CONNECT = 3 # ثانیه

async def check_port(host, port, timeout=TIMEOUT_CONNECT):
    """تست اتصال TCP به پورت"""
    try:
        _, writer = await asyncio.wait_for(
            asyncio.open_connection(host, int(port)), timeout=timeout
        )
        writer.close()
        await writer.wait_closed()
        return True
    except:
        return False

def parse_vmess(conf):
    """استخراج هاست و پورت از لینک VMess"""
    try:
        # حذف پیشوند
        b64_str = conf.replace("vmess://", "")
        # دیکد کردن Base64 (مدیریت پدینگ)
        missing_padding = len(b64_str) % 4
        if missing_padding:
            b64_str += '=' * (4 - missing_padding)
        
        decoded_data = base64.b64decode(b64_str).decode('utf-8')
        data = json.loads(decoded_data)
        
        # در استاندارد vmess، آدرس در 'add' و پورت در 'port' است
        return data.get('add'), data.get('port')
    except Exception:
        return None, None

def extract_host_port(conf):
    """تابع هوشمند برای استخراج آدرس از انواع پروتکل‌ها"""
    host, port = None, None
    
    if conf.startswith("vmess://"):
        host, port = parse_vmess(conf)
    else:
        # برای vless, trojan, ss, tuic و ...
        try:
            # استفاده از urlparse برای دقت بالاتر
            # برخی لینک‌ها ممکن است اسکیم کامل نداشته باشند، پس یک پیش‌فرض اضافه می‌کنیم اگر لازم بود
            if "://" not in conf:
                parsed = urlparse("//" + conf)
            else:
                parsed = urlparse(conf)
            
            host = parsed.hostname
            port = parsed.port
            
            # اگر پارسر استاندارد شکست خورد، روش regex قدیمی شما به عنوان فال‌بک
            if not host or not port:
                match = re.search(r'@([^:/?#]+):(\d+)', conf)
                if match:
                    host = match.group(1)
                    port = int(match.group(2))
        except:
            pass
            
    return host, port

def clean_config(conf):
    # حذف کاراکترهای اضافی انتهای خط
    conf = re.sub(r'[)\\\n\r\t ]+$', '', conf)
    # حذف تگ‌های HTML اگر وجود داشت
    conf = re.sub(r'<[^>]+>', '', conf)
    return conf.strip()

async def main():
    if not SESSION_STRING:
        print("❌ Error: SESSION_STRING not found!")
        return

    async with TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH, connection=ConnectionTcpFull) as client:
        print("🚀 Connected via Telethon.")
        
        all_raw_configs = []
        # الگوی regex بهبود یافته
        # این الگو سعی می‌کند کانفیگ را تا رسیدن به فضای خالی یا کاراکترهای غیرمجاز URL بگیرد
        pattern = r'(vmess://[\w+/=]+|vless://[^#\s\n]+|ss://[^#\s\n]+|trojan://[^#\s\n]+|tuic://[^#\s\n]+|hysteria2?://[^#\s\n]+)'
        
        print("📥 Collecting configs...")
        for channel in CHANNELS:
            try:
                # استفاده از get_entity برای اطمینان از وجود کانال
                entity = await client.get_entity(channel)
                msg_count = 0
                async for message in client.iter_messages(entity, limit=SEARCH_LIMIT):
                    if message.text:
                        found = re.findall(pattern, message.text)
                        for conf in found:
                            cleaned = clean_config(conf)
                            if cleaned:
                                all_raw_configs.append(cleaned)
                    msg_count += 1
                print(f"   ✅ @{channel}: Scanned {msg_count} msgs.")
            except Exception as e:
                print(f"   ⚠️ Error @{channel}: {e}")

        # حذف تکراری‌ها
        unique_configs = list(set(all_raw_configs))
        print(f"🔍 Total unique configs: {len(unique_configs)}")
        
        valid_configs = []
        sem = asyncio.Semaphore(50) # افزایش همزمانی به ۵۰

        async def validate_wrapper(conf):
            # اگر به تعداد کافی رسیدیم، ادامه نده (Optional)
            # نکته: در پردازش موازی دقیق، این شرط ممکن است کمی بیشتر از حد رد شود که اشکالی ندارد
            if len(valid_configs) >= TOTAL_FINAL_COUNT:
                return

            host, port = extract_host_port(conf)
            
            if host and port:
                async with sem:
                    if await check_port(host, port):
                        valid_configs.append(conf)
            else:
                # اگر نتوانستیم پارس کنیم، ریسک نمی‌کنیم و اضافه نمی‌کنیم (یا می‌توانید در یک لیست log ذخیره کنید)
                pass

        print("⚡ Testing connectivity (TCP)...")
        
        # استفاده از progress bar اگر تعداد زیاد است
        tasks = [validate_wrapper(conf) for conf in unique_configs]
        
        # اجرای تسک‌ها
        # اگر tqdm نصب باشد نوار پیشرفت نمایش داده می‌شود
        await tqdm.gather(*tasks)

        print(f"📊 Validation finished. Valid: {len(valid_configs)} / {len(unique_configs)}")

        if valid_configs:
            # شافل کردن لیست برای اینکه بار روی سرورهای اول لیست نیفتد
            import random
            random.shuffle(valid_configs)
            
            final_list = valid_configs[:TOTAL_FINAL_COUNT]
            content_str = "\n".join(final_list)
            
            encoded = base64.b64encode(content_str.encode('utf-8')).decode('utf-8')
            
            with open("sub.txt", "w", encoding='utf-8') as f:
                f.write(encoded)
                
            with open("sub_raw.txt", "w", encoding='utf-8') as f:
                f.write(content_str)
                
            print(f"✨ Saved {len(final_list)} configs to sub.txt")
        else:
            print("⚠️ No valid configs found.")

if __name__ == '__main__':
    asyncio.run(main())

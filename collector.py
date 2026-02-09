import os
import re
import base64
import json
import asyncio
from urllib.parse import urlparse, unquote
from telethon import TelegramClient
from telethon.sessions import StringSession

# ---------------- CONFIGURATION ----------------
API_ID = int(os.environ.get("API_ID", 34146126))
API_HASH = os.environ.get("API_HASH", "6f3350e049ef37676b729241f5bc8c5e")
SESSION_STRING = os.environ.get("SESSION_STRING")

CHANNELS = [
    'napsternetv',
    'v2rayng_org',
    'v2ray_outlineir',
    'free_v2ray_configs',
    'v2ray_custom',
    'SafeNet_Server'
]

# تعداد کانفیگ نهایی برای ذخیره
TOTAL_FINAL_COUNT = 100
# تایم‌اوت تست اتصال (ثانیه)
TIMEOUT = 3

# ---------------- HELPERS ----------------

def decode_vmess(vmess_url):
    """استخراج اطلاعات از لینک VMess"""
    try:
        b64 = vmess_url.replace("vmess://", "")
        padding = len(b64) % 4
        if padding:
            b64 += "=" * (4 - padding)
        decoded = base64.b64decode(b64).decode('utf-8')
        data = json.loads(decoded)
        # return: host, port, name(ps)
        return data.get('add'), int(data.get('port')), data.get('ps', '')
    except:
        return None, None, None

def parse_config(conf):
    """استخراج هاست، پورت و نام کانفیگ"""
    host, port, name = None, None, ""
    
    try:
        if conf.startswith("vmess://"):
            host, port, name = decode_vmess(conf)
        else:
            # برای vless, trojan, ss, etc.
            parsed = urlparse(conf)
            host = parsed.hostname
            port = parsed.port
            # نام کانفیگ معمولاً بعد از # است (fragment)
            if parsed.fragment:
                name = unquote(parsed.fragment) # تبدیل کدهای درصد دار به متن
            
            # هندل کردن حالت‌های خاص که urlparse ممکن است گیج شود
            if not host and '@' in conf:
                match = re.search(r'@([^/:]+):(\d+)', conf)
                if match:
                    host = match.group(1)
                    port = int(match.group(2))
    except Exception:
        pass

    # اگر اسمی پیدا نشد، از ترکیب هاست و پورت استفاده کن که حذف نشود
    if not name and host:
        name = f"{host}:{port}"

    return host, port, name

async def check_connection(host, port, config, semaphore):
    """تست سریع اتصال TCP"""
    if not host or not port:
        return None

    async with semaphore:
        try:
            fut = asyncio.open_connection(host, port)
            reader, writer = await asyncio.wait_for(fut, timeout=TIMEOUT)
            writer.close()
            await writer.wait_closed()
            return config
        except:
            return None

# ---------------- MAIN ----------------

async def main():
    if not SESSION_STRING:
        print("❌ خطا: SESSION_STRING یافت نشد.")
        return

    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    
    try:
        print("🚀 در حال اتصال به تلگرام...")
        await client.connect()
        if not await client.is_user_authorized():
            print("❌ سشن نامعتبر است.")
            return

        all_configs = []
        # پترن RegEx کامل
        pattern = r'(vmess://[\w+/=]+|vless://\S+|ss://\S+|trojan://\S+|tuic://\S+|hysteria2?://\S+)'

        print("📥 در حال اسکن کانال‌ها (این کار ممکن است کمی طول بکشد)...")
        for channel in CHANNELS:
            try:
                # لیمیت را 300 گذاشتیم تا پیام‌های بیشتری بررسی شود
                async for message in client.iter_messages(channel, limit=300):
                    if message.text:
                        found = re.findall(pattern, message.text)
                        for conf in found:
                            # تمیزکاری انتهای لینک
                            conf = re.sub(r'[)\]}"\'>]+$', '', conf)
                            all_configs.append(conf)
            except Exception as e:
                print(f"⚠️ خطا در کانال {channel}: {e}")

        print(f"🔍 تعداد کل کانفیگ‌های خام پیدا شده: {len(all_configs)}")

        # --- مرحله 1: حذف نام‌های تکراری ---
        unique_name_configs = []
        seen_names = set()
        seen_hosts = set() # برای جلوگیری از تکرار خود سرور هم چک می‌کنیم

        print("♻️ در حال فیلتر کردن نام‌های تکراری...")
        
        for conf in all_configs:
            host, port, name = parse_config(conf)
            
            if host and name:
                # نرمال‌سازی نام (حذف فاصله و حروف کوچک)
                clean_name = name.strip().lower()
                clean_host = host.strip().lower()

                # شرط: نه اسم تکراری باشد، نه خود سرور تکراری باشد
                if clean_name not in seen_names and clean_host not in seen_hosts:
                    seen_names.add(clean_name)
                    seen_hosts.add(clean_host)
                    unique_name_configs.append((host, port, conf))
        
        print(f"📉 تعداد کانفیگ‌ها پس از حذف نام‌های تکراری: {len(unique_name_configs)}")

        # --- مرحله 2: تست اتصال (Async) ---
        print("⚡ شروع تست اتصال...")
        
        valid_configs = []
        semaphore = asyncio.Semaphore(100) # افزایش سرعت تست همزمان
        tasks = []

        for host, port, conf in unique_name_configs:
            task = check_connection(host, port, conf, semaphore)
            tasks.append(task)

        results = await asyncio.gather(*tasks)

        for res in results:
            if res:
                valid_configs.append(res)
                if len(valid_configs) >= TOTAL_FINAL_COUNT:
                    break
        
        print(f"✅ تعداد کانفیگ‌های سالم نهایی: {len(valid_configs)}")

        # --- ذخیره ---
        if valid_configs:
            content_str = "\n".join(valid_configs)
            encoded = base64.b64encode(content_str.encode('utf-8')).decode('utf-8')
            with open("sub.txt", "w") as f:
                f.write(encoded)
            print("💾 فایل sub.txt آپدیت شد.")
        else:
            print("⚠️ کانفیگ سالمی پیدا نشد.")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())

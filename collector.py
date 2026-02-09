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
    'free_v2ray_configs'
]

# تعداد کانفیگ نهایی که می‌خواهید ذخیره شود
TOTAL_FINAL_COUNT = 100
# تایم‌اوت تست اتصال (ثانیه) - کمتر = سخت‌گیرتر و سریع‌تر
TIMEOUT = 2 

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
        # return: host, port, remarks
        return data.get('add'), int(data.get('port')), data.get('ps', 'vmess')
    except:
        return None, None, None

def parse_config(conf):
    """تشخیص نوع کانفیگ و استخراج آدرس و پورت"""
    host, port, remarks = None, None, None
    
    try:
        if conf.startswith("vmess://"):
            host, port, remarks = decode_vmess(conf)
        else:
            # برای vless, trojan, ss, etc.
            # فرمت معمول: protocol://uuid@host:port?params#remarks
            parsed = urlparse(conf)
            host = parsed.hostname
            port = parsed.port
            remarks = parsed.fragment
            
            # هندل کردن حالت‌های خاص که urlparse ممکن است گیج شود
            if not host and '@' in conf:
                # تلاش برای استخراج دستی با Regex
                match = re.search(r'@([^/:]+):(\d+)', conf)
                if match:
                    host = match.group(1)
                    port = int(match.group(2))
    except Exception:
        pass

    return host, port

async def check_connection(host, port, config, semaphore):
    """تست سریع اتصال TCP (شبیه پینگ اما روی پورت خاص)"""
    if not host or not port:
        return None

    async with semaphore:  # محدود کردن تعداد تست‌های همزمان
        try:
            # تلاش برای اتصال به پورت مشخص شده سرور
            # اگر این وصل شود یعنی سرور روشن است و روی آن پورت گوش می‌دهد
            fut = asyncio.open_connection(host, port)
            reader, writer = await asyncio.wait_for(fut, timeout=TIMEOUT)
            
            writer.close()
            await writer.wait_closed()
            return config  # کانفیگ سالم است
        except:
            return None  # کانفیگ تایم‌اوت شد یا رد شد

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
        pattern = r'(vmess://[\w+/=]+|vless://\S+|ss://\S+|trojan://\S+|tuic://\S+|hysteria2?://\S+)'

        print("📥 در حال جمع‌آوری پیام‌ها...")
        for channel in CHANNELS:
            try:
                async for message in client.iter_messages(channel, limit=150):
                    if message.text:
                        found = re.findall(pattern, message.text)
                        for conf in found:
                            # تمیزکاری انتهای لینک
                            conf = re.sub(r'[)\]}"\'>]+$', '', conf)
                            all_configs.append(conf)
            except Exception as e:
                print(f"⚠️ خطا در کانال {channel}: {e}")

        print(f"🔍 تعداد کل کانفیگ‌های خام: {len(all_configs)}")

        # --- مرحله 1: حذف تکراری‌ها بر اساس هاست ---
        unique_host_configs = []
        seen_hosts = set()

        print("♻️ در حال حذف سرورهای تکراری...")
        for conf in all_configs:
            host, port = parse_config(conf)
            
            if host:
                # تبدیل به حروف کوچک برای مقایسه دقیق
                host_key = host.lower()
                
                # اگر این هاست را قبلا ندیده‌ایم، اضافه کن
                if host_key not in seen_hosts:
                    seen_hosts.add(host_key)
                    unique_host_configs.append((host, port, conf))
        
        print(f"📉 تعداد کانفیگ‌ها پس از حذف تکراری: {len(unique_host_configs)}")

        # --- مرحله 2: تست سرعت بالا (Async) ---
        print("⚡ شروع تست اتصال (TCP check)...")
        
        valid_configs = []
        semaphore = asyncio.Semaphore(50)  # تست همزمان ۵۰ کانفیگ
        tasks = []

        # ایجاد تسک‌ها
        for host, port, conf in unique_host_configs:
            task = check_connection(host, port, conf, semaphore)
            tasks.append(task)

        # اجرای همزمان همه تست‌ها
        results = await asyncio.gather(*tasks)

        # جمع‌آوری نتایج موفق
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
            print("💾 فایل sub.txt با موفقیت ذخیره شد.")
        else:
            print("⚠️ هیچ کانفیگ سالمی باقی نماند.")

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())

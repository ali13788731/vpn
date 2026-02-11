import os
import re
import base64
import json
import asyncio
import socket
import random
from urllib.parse import urlparse, parse_qs, unquote
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.network import ConnectionTcpFull

# --- تنظیمات ---
API_ID = 34146126
API_HASH = os.environ.get("API_HASH", "6f3350e049ef37676b729241f5bc8c5e")
SESSION_STRING = os.environ.get("SESSION_STRING")

# لیست کانال‌ها (می‌توانید کانال‌های بیشتری اضافه کنید)
CHANNELS = [
    'napsternetv', 'v2rayng_org', 'v2rayng_vpn', 'free_v2rayyy', 
    'v2ray_outlineir', 'PrivateVPNs', 'DirectVPN'
]
SEARCH_LIMIT = 500  # تعداد پیام‌هایی که چک می‌کند (بیشتر کردم تا شانس پیدا کردن متنوع بیشتر شود)
TOTAL_FINAL_COUNT = 80 # تعداد نهایی کمتر ولی با کیفیت‌تر
DUPLICATE_WORD_THRESHOLD = 3 # حساسیت روی نام تکراری

def clean_vmess_key(config):
    """رفع مشکل پدینگ در Base64"""
    missing_padding = len(config) % 4
    if missing_padding:
        config += '=' * (4 - missing_padding)
    return config

def extract_details(config_link):
    """
    آدرس سرور (Host) و نام (Name) را از انواع لینک‌ها استخراج می‌کند.
    خروجی: (host, port, name) یا (None, None, None)
    """
    try:
        config_link = config_link.strip()
        
        # --- VMESS ---
        if config_link.startswith("vmess://"):
            b64 = config_link.replace("vmess://", "")
            decoded = base64.b64decode(clean_vmess_key(b64)).decode('utf-8')
            data = json.loads(decoded)
            return data.get("add", ""), data.get("port", ""), data.get("ps", "")

        # --- VLESS / TROJAN / TUIC / HYSTERIA ---
        # این پروتکل‌ها ساختار مشابه URL دارند: protocol://user@host:port?query#name
        parsed = urlparse(config_link)
        
        host = parsed.hostname
        port = parsed.port
        name = unquote(parsed.fragment) # چیزی که بعد از # هست
        
        if not host: # تلاش دوم با regex برای لینک‌های ناقص
            match = re.search(r'@([^:]+):', config_link)
            if match:
                host = match.group(1)
        
        return host, port, name

    except Exception:
        return None, None, None

def get_clean_words(text):
    """تبدیل نام به مجموعه‌ای از کلمات تمیز برای مقایسه"""
    if not text:
        return set()
    # حذف همه چیز جز حروف و اعداد
    clean_text = re.sub(r'[^\w\s]', '', text).lower()
    words = clean_text.split()
    # کلمات زیر 3 حرف ارزش مقایسه ندارند
    return set([w for w in words if len(w) > 2])

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

        print("🚀 شروع اسکن سنگین و سخت‌گیرانه...")
        
        # پروتکل‌های مجاز (SS حذف شده)
        pattern = r'(vmess|vless|trojan|tuic|hysteria2?)://\S+'
        
        unique_configs = []
        seen_hosts = set() # برای ذخیره آدرس سرورها (جلوگیری از تکرار شرکت)
        seen_names_words = [] # برای ذخیره کلمات نام‌ها

        # اسکن کانال‌ها
        # نکته: ما اول همه را جمع نمی‌کنیم، بلکه حین جمع‌آوری فیلتر می‌کنیم تا سریع‌تر پر شود
        collected_count = 0
        
        for channel in CHANNELS:
            if collected_count >= TOTAL_FINAL_COUNT:
                break
                
            print(f"📡 بررسی دقیق @{channel}...")
            try:
                async for message in client.iter_messages(channel, limit=SEARCH_LIMIT):
                    if collected_count >= TOTAL_FINAL_COUNT:
                        break

                    if message.text:
                        links = re.findall(pattern, message.text)
                        
                        for conf in links:
                            # پاکسازی اولیه
                            conf = conf.strip().split('\n')[0]
                            conf = re.sub(r'[)\]}"\'>]+$', '', conf)

                            # استخراج اطلاعات فنی
                            host, port, name = extract_details(conf)
                            
                            # 1. فیلتر مهم: اگر هاست یا پورت پیدا نشد، ولش کن
                            if not host:
                                continue
                                
                            # نرمال‌سازی هاست (کوچک کردن حروف)
                            host = host.lower()

                            # 2. فیلتر سخت‌گیرانه سرور (IP/Domain تکراری ممنوع)
                            # اگر این هاست قبلا دیده شده، یعنی از این شرکت کانفیگ داریم -> حذف
                            if host in seen_hosts:
                                continue

                            # 3. فیلتر سخت‌گیرانه نام (کلمات تکراری)
                            # اگر هاست جدید است اما نامش خیلی شبیه قبلی‌هاست -> حذف
                            is_duplicate_name = False
                            if name:
                                new_words = get_clean_words(name)
                                if len(new_words) > 0:
                                    for existing_words in seen_names_words:
                                        common = new_words.intersection(existing_words)
                                        if len(common) >= DUPLICATE_WORD_THRESHOLD:
                                            is_duplicate_name = True
                                            break
                                    
                                    if is_duplicate_name:
                                        continue
                                    
                                    # اگر تایید شد، کلماتش را ذخیره کن
                                    seen_names_words.append(new_words)
                            
                            # --- تایید نهایی ---
                            seen_hosts.add(host) # این سرور را به لیست دیده‌شده‌ها اضافه کن
                            
                            # اصلاح نام اگر خالی بود
                            final_conf = conf
                            if not final_conf.startswith("vmess://") and "#" not in final_conf:
                                final_conf = f"{final_conf}#Clean_Config_{random.randint(10,99)}"

                            unique_configs.append(final_conf)
                            collected_count += 1
                            
                            if collected_count >= TOTAL_FINAL_COUNT:
                                break
                
            except Exception as e:
                print(f"⚠️ گذر از کانال {channel}: {e}")

        # ذخیره‌سازی
        if unique_configs:
            print(f"💎 تعداد {len(unique_configs)} کانفیگ یونیک از سرورهای مختلف استخراج شد.")
            content_str = "\n".join(unique_configs)
            encoded = base64.b64encode(content_str.encode('utf-8')).decode('utf-8')
            with open("sub.txt", "w") as f:
                f.write(encoded)
        else:
            print("⚠️ هیچ کانفیگی با معیارهای سخت‌گیرانه شما پیدا نشد.")

    except Exception as e:
        print(f"❌ Error Main: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())

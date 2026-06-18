import os
import re
import base64
import asyncio
import random
import json
from datetime import datetime
from zoneinfo import ZoneInfo
import jdatetime
from urllib.parse import urlparse, urlunparse, quote, unquote
from telethon import TelegramClient
from telethon.sessions import StringSession
from telethon.network import ConnectionTcpFull

# --- تنظیمات اولیه ---
raw_api_id = os.environ.get("API_ID")
API_ID = int(raw_api_id) if raw_api_id and raw_api_id.strip() else 34146126

raw_api_hash = os.environ.get("API_HASH")
API_HASH = raw_api_hash if raw_api_hash and raw_api_hash.strip() else "6f3350e049ef37676b729241f5bc8c5e"

SESSION_STRING = os.environ.get("SESSION_STRING")

CHANNELS = ['napsternetv']
SEARCH_LIMIT = 500  # تعداد پیام برای بررسی در هر کانال
TOTAL_FINAL_COUNT = 150 # تعداد نهایی کانفیگ‌ها

def get_persian_time():
    try:
        tehran_tz = ZoneInfo("Asia/Tehran")
        now_tehran = datetime.now(tehran_tz)
        j_date = jdatetime.datetime.fromgregorian(datetime=now_tehran)
        return j_date.strftime("%Y-%m-%d %H:%M")
    except Exception as e:
        print(f"⚠️ Time Error: {e}")
        return datetime.now().strftime("%Y-%m-%d %H:%M")

def apply_clean_ip(conf, clean_ip):
    """
    آی‌پی/دامنه اصلی کانفیگ را با آی‌پی تمیز جایگزین می‌کند.
    """
    if conf.startswith("vmess://"):
        try:
            base64_str = conf[8:]
            # اصلاح پدینگ Base64 در صورت نیاز
            base64_str += "=" * ((4 - len(base64_str) % 4) % 4)
            json_str = base64.b64decode(base64_str).decode('utf-8')
            data = json.loads(json_str)
            
            # ذخیره آدرس قبلی در sni (اگر خالی بود) برای حفظ اتصال
            if not data.get('sni') and data.get('host'):
                data['sni'] = data.get('host')
                
            data['add'] = clean_ip
            new_base64 = base64.b64encode(json.dumps(data).encode('utf-8')).decode('utf-8')
            return f"vmess://{new_base64}"
        except Exception:
            return conf
    else:
        try:
            parsed = urlparse(conf)
            if '@' in parsed.netloc:
                userinfo, host_port = parsed.netloc.split('@', 1)
                if ':' in host_port:
                    host, port = host_port.split(':', 1)
                    new_netloc = f"{userinfo}@{clean_ip}:{port}"
                else:
                    new_netloc = f"{userinfo}@{clean_ip}"
            else:
                new_netloc = parsed.netloc

            new_parsed = parsed._replace(netloc=new_netloc)
            return urlunparse(new_parsed)
        except Exception:
            return conf

def add_name_to_config(conf, time_tag):
    conf = conf.strip()
    if conf.startswith("vmess://"):
        # برای تغییر نام vmess باید دیکود شود (در این نسخه ساده‌سازی شده نام vmess تغییر نمی‌کند)
        return conf

    try:
        parsed = urlparse(conf)
        current_name = unquote(parsed.fragment).strip()
        
        if not current_name:
            new_name = f"@{time_tag}"
        else:
            if time_tag not in current_name:
                new_name = f"{current_name} | {time_tag}"
            else:
                new_name = current_name

        final_fragment = quote(new_name)
        new_parsed = parsed._replace(fragment=final_fragment)
        return urlunparse(new_parsed)
    except Exception:
        return conf

def save_configs(filename, configs):
    """
    تابع کمکی برای ذخیره کردن کانفیگ‌ها در دو فرمت خام و انکود شده
    """
    if not configs:
        return
    
    content_str = "\n".join(configs)
    encoded = base64.b64encode(content_str.encode('utf-8')).decode('utf-8')
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(encoded)
        
    raw_filename = filename.replace(".txt", "_raw.txt")
    with open(raw_filename, "w", encoding="utf-8") as f:
        f.write(content_str)

async def main():
    if not SESSION_STRING:
        print("❌ SESSION_STRING Not Found! Please set it in GitHub Secrets.")
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
            print("❌ Session is invalid or expired.")
            return

        print("✅ Logged in successfully.")
        
        all_normal = []
        all_mci = []
        all_mtn = []
        time_tag = get_persian_time()
        print(f"⏰ Persian Time: {time_tag}")

        for channel in CHANNELS:
            print(f"📡 Scanning @{channel}...")
            try:
                async for message in client.iter_messages(channel, limit=SEARCH_LIMIT):
                    if message.text:
                        links = re.findall(r'(?:vmess|vless|ss|trojan|tuic|hysteria2?)://[^\s\t\n]+', message.text)
                        
                        for conf in links:
                            conf = re.split(r'[\s\n]+', conf)[0]
                            conf = re.sub(r'[)\]}"\'>,]+$', '', conf)
                            
                            final_conf = add_name_to_config(conf, time_tag)
                            if final_conf:
                                all_normal.append(final_conf)
                                # در اینجا می‌توانید به جای mci.ircf.space، ساب‌دامین اختصاصی خودتان را بگذارید
                                all_mci.append(apply_clean_ip(final_conf, "mci.ircf.space"))
                                all_mtn.append(apply_clean_ip(final_conf, "mtn.ircf.space"))
                
                print(f"   found {len(all_normal)} configs so far...")
                await asyncio.sleep(random.randint(2, 5))

            except Exception as e:
                print(f"⚠️ Error scanning {channel}: {e}")

        # حذف تکراری‌ها
        valid_normal = list(dict.fromkeys(all_normal))[:TOTAL_FINAL_COUNT]
        valid_mci = list(dict.fromkeys(all_mci))[:TOTAL_FINAL_COUNT]
        valid_mtn = list(dict.fromkeys(all_mtn))[:TOTAL_FINAL_COUNT]

        if valid_normal:
            save_configs("sub.txt", valid_normal)
            save_configs("sub_mci.txt", valid_mci)
            save_configs("sub_mtn.txt", valid_mtn)
            print(f"✨ Success! Saved 3 types of configs (Normal, MCI, MTN).")
        else:
            print("⚠️ No configs found.")

    except Exception as e:
        print(f"⚠️ Critical Error: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())

import os
import re
import base64
import asyncio
import socket
import json
import urllib.parse
from telethon import TelegramClient
from telethon.sessions import StringSession

# تنظیمات
API_ID = int(os.environ.get("API_ID", 34146126))
API_HASH = os.environ.get("API_HASH", "6f3350e049ef37676b729241f5bc8c5e")
SESSION_STRING = os.environ.get("SESSION_STRING")

CHANNELS = [
    'napsternetv'
]

SEARCH_LIMIT = 500 
TOTAL_FINAL_COUNT = 100

def is_server_alive(host, port, timeout=0.5):
    """تست اتصال TCP کوتاه"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((host, int(port)))
        sock.close()
        return result == 0
    except:
        return False

def parse_vmess(vmess_url):
    """پارس کردن vmess برای استخراج اطلاعات"""
    try:
        b64 = vmess_url.replace("vmess://", "")
        padding = len(b64) % 4
        if padding:
            b64 += "=" * (4 - padding)
        decoded = base64.b64decode(b64).decode('utf-8')
        return json.loads(decoded)
    except:
        return None

def rename_config(conf, base_name, index):
    """
    نام کانفیگ را تغییر می‌دهد.
    مثال: @ChannelName_1
    """
    new_name = f"{base_name}_{index}"
    
    # 1. مدیریت VMESS
    if conf.startswith("vmess://"):
        try:
            data = parse_vmess(conf)
            if data:
                data['ps'] = new_name  # تغییر نام در فیلد ps
                # بازگرداندن به حالت base64
                json_str = json.dumps(data)
                b64_new = base64.b64encode(json_str.encode('utf-8')).decode('utf-8')
                return f"vmess://{b64_new}"
        except:
            return conf

    # 2. مدیریت سایر پروتکل‌ها (VLESS, Trojan, SS, etc)
    # ساختار معمولاً: protocol://uuid@host:port?params#Name
    else:
        try:
            # جدا کردن بخش هشتگ (نام قبلی) اگر وجود داشته باشد
            if '#' in conf:
                main_part = conf.split('#')[0]
            else:
                main_part = conf
            
            # انکد کردن نام جدید برای قرارگیری در URL
            safe_name = urllib.parse.quote(new_name)
            return f"{main_part}#{safe_name}"
        except:
            return conf
    
    return conf

async def main():
    if not SESSION_STRING:
        print("❌ خطا: SESSION_STRING تنظیم نشده است!")
        return

    client = TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH)
    
    try:
        print("🚀 اتصال به تلگرام...")
        await client.connect()
        if not await client.is_user_authorized():
            print("❌ سشن نامعتبر است!")
            return

        print("✅ متصل شد.")
        all_unique_configs = []
        seen_configs = set()
        
        # الگوی جستجو
        pattern = r'(vmess://[\w+/=]+|vless://\S+|ss://\S+|trojan://\S+|tuic://\S+|hysteria2?://\S+)'

        for channel in CHANNELS:
            print(f"📡 اسکن کانال: @{channel}")
            channel_configs = []
            try:
                async for message in client.iter_messages(channel, limit=SEARCH_LIMIT):
                    if not message.text: continue
                    
                    found = re.findall(pattern, message.text)
                    for conf in found:
                        # پاکسازی کاراکترهای اضافه
                        conf = re.sub(r'[)\]}"\'>]+$', '', conf)
                        
                        # جلوگیری از تکراری بودن خام
                        if conf not in seen_configs:
                            seen_configs.add(conf)
                            channel_configs.append(conf)
            except Exception as e:
                print(f"⚠️ خطا در {channel}: {e}")
            
            print(f"   باقت: {len(channel_configs)} کانفیگ.")
            
            # پردازش کانفیگ‌های این کانال
            for idx, conf in enumerate(channel_configs, 1):
                if len(all_unique_configs) >= TOTAL_FINAL_COUNT:
                    break

                host, port = None, None
                
                # استخراج آدرس برای پینگ
                if conf.startswith("vmess://"):
                    data = parse_vmess(conf)
                    if data:
                        host, port = data.get('add'), data.get('port')
                elif "@" in conf:
                    match = re.search(r'@([^:]+):(\d+)', conf)
                    if match:
                        host, port = match.group(1), match.group(2)
                
                # تست اتصال
                is_working = False
                if host and port:
                    if is_server_alive(host, port):
                        is_working = True
                        print(f"   ✅ سالم: {host}:{port}")
                    else:
                        pass # print(f"   ❌ خراب: {host}:{port}")
                else:
                    # اگر نتوانستیم هاست را پیدا کنیم، فرض می‌کنیم سالم است (ریسک)
                    is_working = True 

                if is_working:
                    # >>> اینجا تغییر نام انجام می‌شود <<<
                    # نام کانال را تمیز می‌کنیم (فقط حروف و اعداد)
                    clean_channel_name = re.sub(r'\W+', '', channel)
                    renamed_conf = rename_config(conf, f"@{clean_channel_name}", len(all_unique_configs)+1)
                    all_unique_configs.append(renamed_conf)

        if all_unique_configs:
            content_str = "\n".join(all_unique_configs)
            encoded_sub = base64.b64encode(content_str.encode('utf-8')).decode('utf-8')
            
            with open("sub.txt", "w", encoding="utf-8") as f:
                f.write(encoded_sub)
            print(f"✨ پایان: {len(all_unique_configs)} کانفیگ ذخیره شد.")
        else:
            print("⚠️ هیچ کانفیگ سالمی پیدا نشد.")

    except Exception as e:
        print(f"⚠️ خطای کلی: {e}")
    finally:
        await client.disconnect()

if __name__ == '__main__':
    asyncio.run(main())

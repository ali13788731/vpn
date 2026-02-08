import asyncio
import re
import os
import base64
import json
from telethon import TelegramClient
from telethon.sessions import StringSession

# --- اطلاعات اکانت شما (هاردکد شده برای راحتی) ---
API_ID = 34146126
API_HASH = '6f3350e049ef37676b729241f5bc8c5e'
SESSION_STRING = '1BJWap1sBu1UWJfb7cqBi3CecVPgf22UHnUDZ5lldvPwcPsOQZ9LLEfFdkZbvd8bNn_vOkZZFw66NJWaJQsrNQCs1InUqyCR-7fvyZEGRyI6FlhP4LvJUw44cpuJeBPWJ7HZMmmZhG63WIgpVq1qDx4c8oiqIVxJJoHvYUh2Lx2BFBcucBcUUgYXiVN4RRlCtark9qn5NsHLQoL5KkL9wjYi8ZlvE9RHWyr2nY4vGT7HJBb2nTZxYCZ0WAIMjaIQjDhTY8axhqDz34fj6VyrPjHDpA0NFc1Tr9Y4NtpLaHJhCahPRhjYYjrFKlb4vVFyLKQ6cl-0EN3H-ppGaJtRhS6ehN4JHs5Y='

CHANNELS = [
    'napsternetv', 'v2ray_free_conf', 'V2ray_Alpha', 
    'V2Ray_Vpn_Config', 'v2ray_outline_config', 'v2rayng_org',
    'VmessProtocol', 'FreeVmessAndVless', 'PrivateVPNs', 'v2rayng_vpn'
]

# ریجکس کامل برای پیدا کردن همه مدل کانفیگ
PROTOCOLS = r'(vless|vmess|trojan|ss|hysteria2|tuic)://[a-zA-Z0-9\-_@.:?=&%#~*+/]+'

async def check_latency(host, port, timeout=2):
    try:
        conn = asyncio.open_connection(host, port)
        reader, writer = await asyncio.wait_for(conn, timeout=timeout)
        writer.close()
        try:
            await writer.wait_closed()
        except:
            pass
        return True
    except:
        return False

def parse_config(config):
    try:
        config = config.strip()
        if config.startswith("vmess://"):
            b64 = config.split("://")[1]
            missing_padding = len(b64) % 4
            if missing_padding:
                b64 += '=' * (4 - missing_padding)
            v2_data = json.loads(base64.b64decode(b64).decode('utf-8'))
            return v2_data.get('add'), int(v2_data.get('port'))
        else:
            part = config.split("://")[1]
            if "@" in part:
                address_part = part.split("@")[1]
            else:
                address_part = part
            clean_addr = address_part.split("?")[0].split("#")[0]
            if ":" in clean_addr:
                host, port = clean_addr.rsplit(":", 1)
                host = host.replace("[", "").replace("]", "")
                return host, int(port)
            return None, None
    except:
        return None, None

async def main():
    print("🚀 Running Collector...")
    async with TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH) as client:
        raw_configs = set()
        for channel in CHANNELS:
            try:
                print(f"📥 Scanning {channel}...")
                async for message in client.iter_messages(channel, limit=100):
                    if message.text:
                        found = re.findall(PROTOCOLS, message.text, re.IGNORECASE)
                        for c in found:
                            clean_conf = c.replace('\u200e', '').strip()
                            if len(clean_conf) < 2000:
                                raw_configs.add(clean_conf)
            except Exception as e:
                print(f"⚠️ Error {channel}: {e}")

        print(f"🔍 Found {len(raw_configs)} unique configs. Testing...")

        valid_configs = []
        tasks = []
        config_list = list(raw_configs)

        for conf in config_list:
            host, port = parse_config(conf)
            if host and port:
                tasks.append(check_latency(host, port))
            else:
                tasks.append(asyncio.create_task(asyncio.sleep(0)))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for i, result in enumerate(results):
            if isinstance(result, bool) and result:
                conf = config_list[i]
                if "pbk=" in conf or "sni=" in conf or "fp=" in conf:
                    valid_configs.insert(0, conf)
                else:
                    valid_configs.append(conf)

        final_configs = valid_configs[:100]
        final_text = "\n".join(final_configs)
        
        with open('sub.txt', 'w', encoding='utf-8') as f:
            f.write(base64.b64encode(final_text.encode('utf-8')).decode('utf-8'))
            
        with open('configs.txt', 'w', encoding='utf-8') as f:
            f.write(final_text)

        print(f"✅ Done! Saved {len(final_configs)} configs.")

if __name__ == "__main__":
    asyncio.run(main())

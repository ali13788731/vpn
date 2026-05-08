# channel_viewer.py
import os
import sys
import asyncio
import html
from telethon.sync import TelegramClient
from telethon.sessions import StringSession
from telethon.errors.rpcerrorlist import ChannelInvalidError, ChannelPrivateError

# --- خواندن متغیرها ---
API_ID = os.environ.get('API_ID')
API_HASH = os.environ.get('API_HASH')
SESSION_STRING = os.environ.get('SESSION_STRING')

# اطمینان از وجود متغیرهای اصلی
if not all([API_ID, API_HASH, SESSION_STRING]):
    print("Error: API_ID, API_HASH, and SESSION_STRING must be set in environment variables or GitHub secrets.")
    sys.exit(1)

# گرفتن آیدی کانال از آرگومان ورودی
if len(sys.argv) < 2:
    print("Error: Please provide a channel ID as a command-line argument.")
    sys.exit(1)
CHANNEL_ID = sys.argv[1]

# --- ساختار HTML ---
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="fa" dir="rtl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>پیام‌های کانال {channel_title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Roboto", "Helvetica Neue", Arial, sans-serif;
            background-color: #f0f2f5;
            color: #1c1e21;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background-color: #ffffff;
            border: 1px solid #dddfe2;
            border-radius: 8px;
            padding: 20px;
        }}
        h1 {{
            color: #1877f2;
            border-bottom: 2px solid #f0f2f5;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        .message {{
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            padding: 15px;
            margin-bottom: 15px;
            background-color: #f9f9f9;
        }}
        .message-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            font-size: 0.9em;
            color: #606770;
            margin-bottom: 10px;
        }}
        .message-content {{
            white-space: pre-wrap;
            word-wrap: break-word;
        }}
        .error {{
            color: #d9534f;
            background-color: #f2dede;
            border: 1px solid #ebccd1;
            padding: 15px;
            border-radius: 4px;
        }}
    </style>
</head>
<body>
    <div class="container">
        {content}
    </div>
</body>
</html>
"""

async def main():
    """ تابع اصلی برای اتصال به تلگرام و واکشی پیام‌ها """
    content_html = ""
    channel_title = CHANNEL_ID  # مقدار پیش‌فرض

    async with TelegramClient(StringSession(SESSION_STRING), API_ID, API_HASH) as client:
        try:
            channel_entity = await client.get_entity(CHANNEL_ID)
            channel_title = channel_entity.title
            
            content_html = f"<h1>آخرین ۱۰۰ پیام از کانال «{html.escape(channel_title)}»</h1>"
            messages_html = ""
            
            # واکشی ۱۰۰ پیام آخر
            async for message in client.iter_messages(channel_entity, limit=100):
                if message.text:
                    # فرمت‌بندی تاریخ و محتوا
                    message_date = message.date.strftime('%Y-%m-%d %H:%M:%S')
                    message_text = html.escape(message.text)
                    
                    messages_html += f"""
                    <div class="message">
                        <div class="message-header">
                            <span>شناسه پیام: {message.id}</span>
                            <span>تاریخ: {message_date}</span>
                        </div>
                        <div class="message-content">
                            {message_text}
                        </div>
                    </div>
                    """
            
            if not messages_html:
                messages_html = "<p>هیچ پیام متنی در ۱۰۰ پیام آخر این کانال یافت نشد.</p>"

            content_html += messages_html

        except (ValueError, ChannelInvalidError):
            content_html = f"<div class='error'>خطا: کانال با آیدی '{html.escape(CHANNEL_ID)}' یافت نشد یا نامعتبر است.</div>"
        except ChannelPrivateError:
            content_html = f"<div class='error'>خطا: شما به کانال '{html.escape(CHANNEL_ID)}' دسترسی ندارید (کانال خصوصی است).</div>"
        except Exception as e:
            content_html = f"<div class='error'>یک خطای پیش‌بینی نشده رخ داد: {html.escape(str(e))}</div>"

    # تولید فایل نهایی HTML
    final_html = HTML_TEMPLATE.format(channel_title=html.escape(channel_title), content=content_html)
    with open("channel_view.html", "w", encoding="utf-8") as f:
        f.write(final_html)
    
    print(f"File 'channel_view.html' created successfully for channel '{channel_title}'.")

if __name__ == "__main__":
    asyncio.run(main())

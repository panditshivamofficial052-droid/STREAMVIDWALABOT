import os
import time
import shutil
import logging
import psutil
import aiohttp
from pyrogram import Client, filters, errors, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient
from aiohttp import web
from config import Config
from tv_template_sheffy_samra import tv_template_sheffy_samra

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

START_TIME = time.time()

def get_readable_time(seconds: int) -> str:
    count = 0
    ping_time = ""
    time_list = []
    time_suffix_list = ["s", "m", "h", "days"]
    while count < 4:
        count += 1
        remainder, result = divmod(seconds, 60) if count < 3 else divmod(seconds, 24)
        if seconds == 0 and remainder == 0:
            break
        time_list.append(int(result))
        seconds = int(remainder)
    for x in range(len(time_list)):
        time_list[x] = str(time_list[x]) + time_suffix_list[x]
    if len(time_list) == 4:
        ping_time += time_list.pop() + ", "
    time_list.reverse()
    ping_time += ":".join(time_list)
    return ping_time

class StreamBot(Client):
    def __init__(self):
        super().__init__(
            name="FileStreamBot",
            api_id=Config.API_ID,
            api_hash=Config.API_HASH,
            bot_token=Config.BOT_TOKEN
        )
        self.db_client = AsyncIOMotorClient(Config.MONGO_URI)
        self.db = self.db_client.get_database("StreamBot")
        self.settings = self.db.settings
        self.users = self.db.users
        self.public_url = Config.FQDN.rstrip('/')
        self.chunk_size = 1048576 

    async def get_db_settings(self):
        data = await self.settings.find_one({"id": "config"})
        if not data:
            default = {
                "id": "config",
                "fsub": True,
                "sh1": {"status": False, "domain": "", "api": ""},
                "sh2": {"status": False, "domain": "", "api": ""},
                "sh3": {"status": False, "domain": "", "api": ""},
                "sh4": {"status": False, "domain": "", "api": ""},
            }
            await self.settings.insert_one(default)
            return default
        return data

    async def get_shortlink(self, url, domain, api):
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(f'https://{domain}/api?api={api}&url={url}') as res:
                    data = await res.json()
                    return data.get("shortenedUrl") or url
        except Exception as e:
            logger.error(f"Shortener Error: {e}")
            return url

    async def start(self):
        await super().start()
        logger.info(f"Bot & Stream Server starting... Links will use: {self.public_url}")
        
        # Web Server Setup
        app = web.Application()
        app.router.add_get("/", lambda r: web.Response(text="Bot Active"))
        app.router.add_get("/stream/{msg_id}", self.stream_handler)
        app.router.add_get("/download/{msg_id}", self.stream_handler) # Native download route
        app.router.add_get("/watch/{msg_id}", self.watch_handler)
        app.router.add_get("/thumb/{msg_id}", self.thumb_handler) # Thumbnail route
        runner = web.AppRunner(app)
        await runner.setup()
        await web.TCPSite(runner, Config.BIND_ADRESS, Config.PORT).start()

    async def thumb_handler(self, request):
        try:
            msg_id = int(request.match_info['msg_id'])
            file_msg = await self.get_messages(Config.BIN_CHANNEL, msg_id)
            if not file_msg:
                return web.Response(status=404)

            file = file_msg.document or file_msg.video or file_msg.audio
            if not file or not getattr(file, 'thumbs', None):
                return web.Response(status=404)

            thumb = file.thumbs[0]
            thumb_data = await self.download_media(thumb.file_id, in_memory=True)
            return web.Response(body=thumb_data.getvalue(), content_type="image/jpeg")
        except Exception as e:
            logger.error(f"Thumbnail error: {e}")
            return web.Response(status=404)

    async def watch_handler(self, request):
        try:
            msg_id = int(request.match_info['msg_id'])
            file_msg = await self.get_messages(Config.BIN_CHANNEL, msg_id)
            if not file_msg:
                return web.Response(text="File not found", status=404)
            
            file = file_msg.document or file_msg.video or file_msg.audio
            if not file:
                return web.Response(text="Invalid file type", status=400)

            stream_url = f"{self.public_url}/stream/{msg_id}"
            download_url = f"{self.public_url}/download/{msg_id}"
            thumb_url = f"{self.public_url}/thumb/{msg_id}"
            file_name = getattr(file, 'file_name', None) or f"File_{msg_id}"
            mime_type = getattr(file, 'mime_type', None) or "video/mp4"

            html_content = tv_template_sheffy_samra.replace("[[STREAM_URL]]", stream_url)
            html_content = html_content.replace("[[DOWNLOAD_URL]]", download_url)
            html_content = html_content.replace("[[THUMB_URL]]", thumb_url)
            html_content = html_content.replace("[[FILE_NAME]]", file_name)
            html_content = html_content.replace("[[MIME_TYPE]]", mime_type)

            return web.Response(text=html_content, content_type='text/html')
        except Exception as e:
            logger.error(f"Watch handler error: {e}")
            return web.HTTPInternalServerError()

    async def stream_handler(self, request):
        try:
            msg_id = int(request.match_info['msg_id'])
            file_msg = await self.get_messages(Config.BIN_CHANNEL, msg_id)
            
            if not file_msg:
                return web.Response(status=404, text="Message not found in database")
                
            file = file_msg.document or file_msg.video or file_msg.audio
            if not file:
                return web.Response(status=404, text="Media not found in message")
            
            file_size = getattr(file, 'file_size', 0)
            file_name = getattr(file, 'file_name', None) or f"File_{msg_id}"
            mime_type = getattr(file, 'mime_type', None) or "application/octet-stream"

            is_download = "download" in request.path
            disposition = "attachment" if is_download else "inline"

            headers = {
                "Content-Type": mime_type,
                "Content-Disposition": f'{disposition}; filename="{file_name}"',
                "Accept-Ranges": "bytes",
            }
            
            range_header = request.headers.get("Range")
            
            if range_header:
                start, end = range_header.replace("bytes=", "").split("-")
                start = int(start) if start else 0
                end = int(end) if end else file_size - 1
                length = end - start + 1
                
                headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
                headers["Content-Length"] = str(length)
                
                response = web.StreamResponse(status=206, headers=headers)
                await response.prepare(request)
                
                offset_chunk = start // self.chunk_size
                skip_bytes = start % self.chunk_size
                
                try:
                    async for chunk in self.stream_media(file_msg, limit=0, offset=offset_chunk):
                        if not chunk:
                            break
                            
                        if skip_bytes > 0:
                            chunk = chunk[skip_bytes:]
                            skip_bytes = 0
                            
                        if len(chunk) > length:
                            chunk = chunk[:length]
                            
                        await response.write(chunk)
                        length -= len(chunk)
                        
                        if length <= 0:
                            break
                            
                except Exception as e:
                    if "closing transport" in str(e).lower() or "connection reset" in str(e).lower() or "broken pipe" in str(e).lower():
                        pass
                    else:
                        logger.error(f"Streaming connection closed abruptly: {e}")
                return response
                
            else:
                headers["Content-Length"] = str(file_size)
                response = web.StreamResponse(status=200, headers=headers)
                await response.prepare(request)
                
                try:
                    async for chunk in self.stream_media(file_msg):
                        if not chunk:
                            break
                        await response.write(chunk)
                except Exception as e:
                    if "closing transport" in str(e).lower() or "connection reset" in str(e).lower() or "broken pipe" in str(e).lower():
                        pass
                    else:
                        logger.error(f"Streaming connection closed abruptly: {e}")
                return response
                
        except Exception as e: 
            logger.error(f"Stream handler setup error: {e}")
            return web.HTTPInternalServerError()

bot = StreamBot()

@bot.on_message(filters.command(["setfsub", "setsh1st", "setsh2nd", "setsh3rd", "setsh4th"]) & filters.user(Config.OWNER_ID))
async def toggle_settings(c, m: Message):
    cmd = m.command[0]
    state = m.command[1].lower() == "on" if len(m.command) > 1 else False
    
    if cmd == "setfsub":
        key = "fsub"
        await c.settings.update_one({"id": "config"}, {"$set": {"fsub": state}})
    else:
        # e.g. cmd = "setsh1st" -> key = "sh1"
        num = cmd[5:6] 
        key = f"sh{num}"
        await c.settings.update_one({"id": "config"}, {"$set": {f"{key}.status": state}})
        
    await m.reply(f"✅ <b>{key.upper()}</b> set to <b>{'ON' if state else 'OFF'}</b>", parse_mode=enums.ParseMode.HTML)

@bot.on_message(filters.command(["1stdomain", "2nddomain", "3rddomain", "4thdomain", "1stapi", "2ndapi", "3rdapi", "4thapi"]) & filters.user(Config.OWNER_ID))
async def update_configs(c, m: Message):
    if len(m.command) < 2: return await m.reply("Usage: /command <value>")
    cmd = m.command[0]
    val = m.command[1]
    num = cmd[0] # gets '1', '2', '3', or '4'
    field = "domain" if "domain" in cmd else "api"
    
    await c.settings.update_one({"id": "config"}, {"$set": {f"sh{num}.{field}": val}})
    await m.reply(f"✅ Updated Shortener <b>{num}</b> <b>{field}</b>", parse_mode=enums.ParseMode.HTML)

@bot.on_message(filters.command("smdetails") & filters.user(Config.OWNER_ID))
async def smdetails_cmd(c: StreamBot, m: Message):
    db = await c.get_db_settings()
    total_users = await c.users.count_documents({})
    
    # System Stats calculation
    total, used, free = shutil.disk_usage("/")
    ram = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=0.5)
    uptime_str = get_readable_time(int(time.time() - START_TIME))
    
    text = f"⚙️ **System Details & Bot Stats**\n\n"
    text += f"👥 **Total Users:** `{total_users}`\n"
    text += f"⏱ **Uptime:** `{uptime_str}`\n"
    text += f"💻 **CPU Usage:** `{cpu}%`\n"
    text += f"💾 **RAM Usage:** `{ram.percent}%`\n"
    text += f"💿 **Storage Free:** `{free // (2**30)} GB / {total // (2**30)} GB`\n\n"
    
    text += f"🔗 **Shorteners Status:**\n"
    for i in range(1, 5):
        sh = db[f'sh{i}']
        status = "✅ ON" if sh['status'] else "❌ OFF"
        text += f"**Shortener {i}:** {status}\n"
        text += f" ├ Domain: `{sh['domain'] or 'Not Set'}`\n"
        text += f" └ API: `{sh['api'] or 'Not Set'}`\n\n"
        
    await m.reply(text)

@bot.on_message(filters.command("start") & filters.private)
async def start_msg(c, m: Message):
    if not await c.users.find_one({"user_id": m.from_user.id}):
        await c.users.insert_one({"user_id": m.from_user.id, "name": m.from_user.first_name})
    
    # Updated generic welcoming text for all users
    text = (
        f"<blockquote>👋 <b>Hello {m.from_user.first_name}! Welcome to the Ultimate Stream Bot!</b>\n\n"
        f"I can convert your Telegram files into high-speed streaming and download links instantly.\n\n"
        f"🎯 <b>How to use me?</b>\n"
        f"Just send or forward me any video, audio, or document file, and I will generate your personalized links!</blockquote>"
    )
    
    buttons = []
    if Config.FORCE_SUB_CHANNEL:
        buttons.append([InlineKeyboardButton("📢 Join Updates Channel", url=f"https://t.me/{Config.FORCE_SUB_CHANNEL}")])
        
    await m.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons) if buttons else None,
        parse_mode=enums.ParseMode.HTML
    )

@bot.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def handle_file(c: StreamBot, m: Message):
    db = await c.get_db_settings()
    
    if db['fsub'] and Config.FORCE_SUB_CHANNEL:
        try:
            await c.get_chat_member(Config.FORCE_SUB_CHANNEL, m.from_user.id)
        except errors.UserNotParticipant:
            invite_link = (await c.get_chat(Config.FORCE_SUB_CHANNEL)).invite_link
            return await m.reply(
                "<blockquote>❌ <b>Join Channel First!</b>\n\nYou must join our channel to use this bot for streaming.</blockquote>",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Join Now", url=invite_link or f"https://t.me/{Config.FORCE_SUB_CHANNEL}")]]),
                parse_mode=enums.ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Fsub Error: {e}")

    processing_msg = await m.reply("<i>Processing your file...</i>", parse_mode=enums.ParseMode.HTML)

    bin_msg = await m.forward(Config.BIN_CHANNEL)
    
    watch_url = f"{c.public_url}/watch/{bin_msg.id}"
    download_url = f"{c.public_url}/download/{bin_msg.id}"
    
    file = m.document or m.video or m.audio
    file_name = getattr(file, 'file_name', None) or f"File_{bin_msg.id}"
    
    # Start building the response text
    text = f"<blockquote>📁 <b>File Name:</b> <code>{file_name}</code>\n\n"
    text += f"👇 <b>Tap on links to copy</b> 👇\n\n"
    
    buttons = []
    shorteners_used = False
    
    # Process the 4 shorteners dynamically
    for i in range(1, 5):
        sh = db[f'sh{i}']
        if sh['status'] and sh['domain'] and sh['api']:
            shorteners_used = True
            short = await c.get_shortlink(watch_url, sh['domain'], sh['api'])
            domain_name = sh['domain']
            
            # Post me File name + Short link
            text += f"🌐 <b>{domain_name}:</b>\n👉 <code>{short}</code>\n\n"
            
            # Button to directly share/copy that specific link via Telegram's share dialog
            buttons.append([InlineKeyboardButton(f"🔗 Share/Copy {domain_name}", url=f"https://t.me/share/url?url={short}")])
            
    # Fallback if no shorteners are active
    if not shorteners_used:
        text += f"📺 <b>Watch Link:</b>\n👉 <code>{watch_url}</code>\n\n"
        text += f"📥 <b>Download Link:</b>\n👉 <code>{download_url}</code>\n"
        buttons.append([InlineKeyboardButton("▶️ Watch Online", url=watch_url)])
        buttons.append([InlineKeyboardButton("📥 Fast Download", url=download_url)])

    text += "</blockquote>"
    
    await processing_msg.delete()
    await m.reply_text(
        text, 
        reply_markup=InlineKeyboardMarkup(buttons), 
        quote=True, 
        parse_mode=enums.ParseMode.HTML
    )

if __name__ == "__main__":
    bot.run()

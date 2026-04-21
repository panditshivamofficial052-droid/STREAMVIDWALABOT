import os
import time
import shutil
import logging
import psutil
import aiohttp
import asyncio
from pyrogram import Client, idle, filters, errors, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand, BotCommandScopeDefault
from motor.motor_asyncio import AsyncIOMotorClient
from aiohttp import web
from config import Config
from tv_template_sheffy_samra import tv_template_sheffy_samra

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

START_TIME = time.time()

# Dictionary to track admin conversation states
admin_states = {}

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

@bot.on_message(filters.command(["setfsub"]) & filters.user(Config.OWNER_ID))
async def toggle_fsub(c, m: Message):
    state = m.command[1].lower() == "on" if len(m.command) > 1 else False
    await c.settings.update_one({"id": "config"}, {"$set": {"fsub": state}})
    await m.reply(f"✅ <b>FSUB</b> set to <b>{'ON' if state else 'OFF'}</b>", parse_mode=enums.ParseMode.HTML)

# Setup Shorteners with Conversation Logic
@bot.on_message(filters.command(["setsh1st", "setsh2nd", "setsh3rd", "setsh4th"]) & filters.user(Config.OWNER_ID))
async def setup_shorteners(c, m: Message):
    cmd = m.command[0].lower()
    num = cmd[5:6] # Gets '1', '2', '3', or '4'
    
    if len(m.command) < 2:
        return await m.reply(f"<b>Usage:</b> <code>/{cmd} on</code> or <code>/{cmd} off</code>", parse_mode=enums.ParseMode.HTML)
        
    state = m.command[1].lower()
    
    if state == "off":
        await c.settings.update_one({"id": "config"}, {"$set": {f"sh{num}.status": False}})
        if m.from_user.id in admin_states:
            del admin_states[m.from_user.id]
        await m.reply(f"✅ <b>Shortener {num}</b> has been turned <b>OFF</b>.", parse_mode=enums.ParseMode.HTML)
        
    elif state == "on":
        admin_states[m.from_user.id] = {"step": "domain", "num": num}
        await m.reply(f"🟢 <b>Setting up Shortener {num}</b>\n\n👉 Please send the <b>DOMAIN NAME</b> (e.g., <code>shareus.io</code>):", parse_mode=enums.ParseMode.HTML)

# Conversation State Listener
@bot.on_message(filters.private & filters.text & filters.user(Config.OWNER_ID) & ~filters.command(["start", "smdetails", "setfsub", "setsh1st", "setsh2nd", "setsh3rd", "setsh4th"]))
async def state_handler(c, m: Message):
    user_id = m.from_user.id
    
    if user_id in admin_states:
        state_info = admin_states[user_id]
        num = state_info["num"]
        step = state_info["step"]
        
        if step == "domain":
            domain = m.text.strip()
            await c.settings.update_one({"id": "config"}, {"$set": {f"sh{num}.domain": domain}})
            admin_states[user_id]["step"] = "api"
            await m.reply(f"✅ <b>Domain saved:</b> <code>{domain}</code>\n\n👉 Now, please send the <b>API KEY</b>:", parse_mode=enums.ParseMode.HTML)
        
        elif step == "api":
            api = m.text.strip()
            await c.settings.update_one({"id": "config"}, {"$set": {f"sh{num}.api": api, f"sh{num}.status": True}})
            del admin_states[user_id]
            await m.reply(f"🎉 <b>Success!</b>\n\n✅ <b>API saved.</b>\n🟢 <b>Shortener {num} is now completely configured and turned ON!</b>", parse_mode=enums.ParseMode.HTML)

@bot.on_message(filters.command("smdetails") & filters.user(Config.OWNER_ID))
async def smdetails_cmd(c: StreamBot, m: Message):
    db = await c.get_db_settings()
    total_users = await c.users.count_documents({})
    
    total, used, free = shutil.disk_usage("/")
    ram = psutil.virtual_memory()
    cpu = psutil.cpu_percent(interval=0.5)
    uptime_str = get_readable_time(int(time.time() - START_TIME))
    
    text = f"⚙️ <b>System Details & Bot Stats</b>\n\n"
    text += f"👥 <b>Total Users:</b> <code>{total_users}</code>\n"
    text += f"⏱ <b>Uptime:</b> <code>{uptime_str}</code>\n"
    text += f"💻 <b>CPU Usage:</b> <code>{cpu}%</code>\n"
    text += f"💾 <b>RAM Usage:</b> <code>{ram.percent}%</code>\n"
    text += f"💿 <b>Storage Free:</b> <code>{free // (2**30)} GB / {total // (2**30)} GB</code>\n\n"
    
    text += f"🔗 <b>Shorteners Status:</b>\n\n"
    for i in range(1, 5):
        sh = db[f'sh{i}']
        status = "✅ <b>ON</b>" if sh['status'] else "❌ <b>OFF</b>"
        text += f"<b>Shortener {i}:</b> {status}\n"
        text += f" ├ <b>Domain:</b> <code>{sh['domain'] or 'Not Set'}</code>\n"
        text += f" └ <b>API:</b> <code>{sh['api'] or 'Not Set'}</code>\n\n"
        
    await m.reply(text, parse_mode=enums.ParseMode.HTML)

@bot.on_message(filters.command("start") & filters.private)
async def start_msg(c, m: Message):
    if not await c.users.find_one({"user_id": m.from_user.id}):
        await c.users.insert_one({"user_id": m.from_user.id, "name": m.from_user.first_name})
    
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
    
    text = f"<blockquote>📁 <b>File Name:</b> <code>{file_name}</code>\n\n"
    text += f"👇 <b>Tap on links to copy</b> 👇\n\n"
    
    buttons = []
    shorteners_used = False
    
    for i in range(1, 5):
        sh = db[f'sh{i}']
        if sh['status'] and sh['domain'] and sh['api']:
            shorteners_used = True
            short = await c.get_shortlink(watch_url, sh['domain'], sh['api'])
            domain_name = sh['domain']
            
            text += f"🌐 <b>{domain_name}:</b>\n👉 <code>{short}</code>\n\n"
            buttons.append([InlineKeyboardButton(f"🔗 Share/Copy {domain_name}", url=f"https://t.me/share/url?url={short}")])
            
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
        disable_web_page_preview=True,
        parse_mode=enums.ParseMode.HTML
    )

async def start_services():
    logger.info("Starting Pyrogram Client...")
    await bot.start()
    
    # ------------------ MENU AUTO SETUP ------------------
    logger.info("Setting Bot Commands Menu...")
    try:
        # Added Scope to FORCE update for all users immediately
        await bot.set_bot_commands([
            BotCommand("start", "🚀 Start The Stream Bot"),
            BotCommand("smdetails", "📊 System & Bot Stats"),
            BotCommand("setfsub", "🔐 Setup Force Sub (Admin)"),
            BotCommand("setsh1st", "🟡 Config 1st Shortener"),
            BotCommand("setsh2nd", "🟢 Config 2nd Shortener"),
            BotCommand("setsh3rd", "🔵 Config 3rd Shortener"),
            BotCommand("setsh4th", "🟣 Config 4th Shortener")
        ], scope=BotCommandScopeDefault())
        logger.info("Commands menu updated successfully!")
    except Exception as e:
        logger.error(f"Failed to set bot commands: {e}")
    # -----------------------------------------------------
    
    logger.info(f"Starting Web Server on {Config.BIND_ADRESS}:{Config.PORT}")
    app = web.Application()
    app.router.add_get("/", lambda r: web.Response(text="Bot Active"))
    app.router.add_get("/stream/{msg_id}", bot.stream_handler)
    app.router.add_get("/download/{msg_id}", bot.stream_handler)
    app.router.add_get("/watch/{msg_id}", bot.watch_handler)
    app.router.add_get("/thumb/{msg_id}", bot.thumb_handler)
    
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, Config.BIND_ADRESS, Config.PORT)
    await site.start()
    
    logger.info("Services started successfully. Idling...")
    await idle()
    
    logger.info("Stopping services...")
    await runner.cleanup()
    await bot.stop()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_services())

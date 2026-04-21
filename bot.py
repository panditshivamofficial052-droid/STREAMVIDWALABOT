import os
import logging
import aiohttp
from pyrogram import Client, filters, errors, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient
from aiohttp import web
from config import Config
from tv_template_sheffy_samra import tv_template_sheffy_samra

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

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
        self.chunk_size = 1048576 # Strict 1MB Chunk limit for Telegram API

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
        app.router.add_get("/watch/{msg_id}", self.watch_handler)
        runner = web.AppRunner(app)
        await runner.setup()
        await web.TCPSite(runner, Config.BIND_ADRESS, Config.PORT).start()

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
            file_name = getattr(file, 'file_name', None) or f"File_{msg_id}"
            mime_type = getattr(file, 'mime_type', None) or "video/mp4"

            # Inject variables into HTML template
            html_content = tv_template_sheffy_samra.replace("[[STREAM_URL]]", stream_url)
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

            headers = {
                "Content-Type": mime_type,
                "Content-Disposition": f'inline; filename="{file_name}"',
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
                
                # Chunk index logic fixed here to prevent OFFSET_INVALID
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
                    # Ignore standard disconnect exceptions
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
    key = "fsub" if cmd == "setfsub" else f"sh{cmd[5:6]}"
    
    if key == "fsub":
        await c.settings.update_one({"id": "config"}, {"$set": {"fsub": state}})
    else:
        await c.settings.update_one({"id": "config"}, {"$set": {f"{key}.status": state}})
    await m.reply(f"✅ <b>{key.upper()}</b> set to <b>{'ON' if state else 'OFF'}</b>", parse_mode=enums.ParseMode.HTML)

@bot.on_message(filters.command(["1stdomain", "2nddomain", "3rddomain", "4thdomain", "1stapi", "2ndapi", "3rdapi", "4thapi"]) & filters.user(Config.OWNER_ID))
async def update_configs(c, m: Message):
    if len(m.command) < 2: return await m.reply("Usage: /command <value>")
    cmd = m.command[0]
    val = m.command[1]
    num = cmd[0]
    field = "domain" if "domain" in cmd else "api"
    await c.settings.update_one({"id": "config"}, {"$set": {f"sh{num}.{field}": val}})
    await m.reply(f"✅ Updated Shortener <b>{num}</b> <b>{field}</b>", parse_mode=enums.ParseMode.HTML)

@bot.on_message(filters.command("start") & filters.private)
async def start_msg(c, m: Message):
    if not await c.users.find_one({"user_id": m.from_user.id}):
        await c.users.insert_one({"user_id": m.from_user.id, "name": m.from_user.first_name})
    
    await m.reply_text(
        f"<blockquote>👋 <b>Hi {m.from_user.first_name}!</b>\n\nI am a high-speed File Stream bot. Just send me any file and I will generate an instant streaming and download link for it.</blockquote>",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Updates Channel", url=f"https://t.me/{Config.FORCE_SUB_CHANNEL}")]]),
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
                "<blockquote>❌ <b>Join Channel First!</b>\n\nYou must join the channel first to stream files.</blockquote>",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Join Now", url=invite_link or f"https://t.me/{Config.FORCE_SUB_CHANNEL}")]]),
                parse_mode=enums.ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Fsub Error: {e}")

    bin_msg = await m.forward(Config.BIN_CHANNEL)
    
    stream_url = f"{c.public_url}/stream/{bin_msg.id}"
    watch_url = f"{c.public_url}/watch/{bin_msg.id}"
    
    final_links = []
    buttons = []
    
    for i in range(1, 5):
        sh = db[f'sh{i}']
        if sh['status'] and sh['domain'] and sh['api']:
            short = await c.get_shortlink(watch_url, sh['domain'], sh['api'])
            final_links.append(f"🔗 <b>Link {i}:</b> <code>{short}</code>")
            buttons.append([InlineKeyboardButton(f"▶️ Watch {i}", url=short)])
    
    if not final_links:
        final_links.append(f"📺 <b>Watch Link:</b> <code>{watch_url}</code>")
        final_links.append(f"📥 <b>Download Link:</b> <code>{stream_url}</code>")
        buttons.append([InlineKeyboardButton("▶️ Watch Online", url=watch_url)])
        buttons.append([InlineKeyboardButton("📥 Fast Download", url=stream_url)])

    text = "<blockquote>✅ <b>Your Links are Ready!</b>\n\n" + "\n".join(final_links) + "</blockquote>"
    await m.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), quote=True, parse_mode=enums.ParseMode.HTML)

if __name__ == "__main__":
    bot.run()

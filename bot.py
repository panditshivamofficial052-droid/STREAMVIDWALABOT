import os
import logging
import aiohttp
from pyrogram import Client, filters, errors
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton
from motor.motor_asyncio import AsyncIOMotorClient
from aiohttp import web
from config import Config

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
        # Removing auto-detect, strictly using FQDN from Config
        self.public_url = Config.FQDN.rstrip('/')

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
        runner = web.AppRunner(app)
        await runner.setup()
        await web.TCPSite(runner, Config.BIND_ADRESS, Config.PORT).start()

    async def stream_handler(self, request):
        try:
            msg_id = int(request.match_info['msg_id'])
            file_msg = await self.get_messages(Config.BIN_CHANNEL, msg_id)
            file = file_msg.document or file_msg.video or file_msg.audio
            
            range_header = request.headers.get("Range")
            offset = int(range_header.replace("bytes=", "").split("-")[0]) if range_header else 0

            res = web.StreamResponse(status=206 if range_header else 200, headers={
                "Content-Type": file.mime_type or "application/octet-stream",
                "Content-Disposition": f'attachment; filename="{file.file_name}"',
                "Accept-Ranges": "bytes",
                "Content-Length": str(file.file_size - offset),
                "Content-Range": f"bytes {offset}-{file.file_size-1}/{file.file_size}"
            })
            await res.prepare(request)
            async for chunk in self.stream_media(file, offset=offset):
                await res.write(chunk)
            return res
        except Exception as e: 
            logger.error(f"Streaming error: {e}")
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
    await m.reply(f"✅ {key.upper()} set to {'ON' if state else 'OFF'}")

@bot.on_message(filters.command(["1stdomain", "2nddomain", "3rddomain", "4thdomain", "1stapi", "2ndapi", "3rdapi", "4thapi"]) & filters.user(Config.OWNER_ID))
async def update_configs(c, m: Message):
    if len(m.command) < 2: return await m.reply("Usage: /command <value>")
    cmd = m.command[0]
    val = m.command[1]
    num = cmd[0]
    field = "domain" if "domain" in cmd else "api"
    await c.settings.update_one({"id": "config"}, {"$set": {f"sh{num}.{field}": val}})
    await m.reply(f"✅ Updated Shortener {num} {field}")

@bot.on_message(filters.command("start") & filters.private)
async def start_msg(c, m: Message):
    if not await c.users.find_one({"user_id": m.from_user.id}):
        await c.users.insert_one({"user_id": m.from_user.id, "name": m.from_user.first_name})
    
    await m.reply_text(
        f"👋 **Hi {m.from_user.first_name}!**\n\nI am a high-speed File Stream bot. Just send me any file and I will generate an instant streaming and download link for it.",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Updates Channel", url=f"https://t.me/{Config.FORCE_SUB_CHANNEL}")]])
    )

@bot.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def handle_file(c: StreamBot, m: Message):
    db = await c.get_db_settings()
    
    # FSub validation logic
    if db['fsub'] and Config.FORCE_SUB_CHANNEL:
        try:
            await c.get_chat_member(Config.FORCE_SUB_CHANNEL, m.from_user.id)
        except errors.UserNotParticipant:
            invite_link = (await c.get_chat(Config.FORCE_SUB_CHANNEL)).invite_link
            return await m.reply(
                "❌ **Join Channel First!**\n\nYou must join the channel first to stream files.",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("Join Now", url=invite_link or f"https://t.me/{Config.FORCE_SUB_CHANNEL}")]])
            )
        except Exception as e:
            logger.error(f"Fsub Error: {e}")

    bin_msg = await m.forward(Config.BIN_CHANNEL)
    stream_url = f"{c.public_url}/stream/{bin_msg.id}"
    
    final_links = []
    buttons = []
    
    # Multi-Shortener Link Iteration
    for i in range(1, 5):
        sh = db[f'sh{i}']
        if sh['status'] and sh['domain'] and sh['api']:
            short = await c.get_shortlink(stream_url, sh['domain'], sh['api'])
            final_links.append(f"🔗 **Link {i}:** `{short}`")
            buttons.append([InlineKeyboardButton(f"Stream/Download {i}", url=short)])
    
    if not final_links:
        final_links.append(f"🔗 **Direct Link:** `{stream_url}`")
        buttons.append([InlineKeyboardButton("Direct Stream", url=stream_url)])

    text = "✅ **Your Links are Ready!**\n\n" + "\n".join(final_links)
    await m.reply_text(text, reply_markup=InlineKeyboardMarkup(buttons), quote=True)

if __name__ == "__main__":
    bot.run()

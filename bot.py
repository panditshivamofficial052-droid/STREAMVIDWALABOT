import os
import re
import time
import shutil
import logging
import psutil
import aiohttp
import asyncio
import pyrogram.utils
from pyrogram import Client, idle, filters, errors, enums
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, BotCommand, BotCommandScopeDefault
from motor.motor_asyncio import AsyncIOMotorClient
from aiohttp import web
from config import Config
from tv_template_sheffy_samra import tv_template_sheffy_samra

# Pyrogram PeerIdInvalid Hack
pyrogram.utils.MIN_CHAT_ID = -999999999999
pyrogram.utils.MIN_CHANNEL_ID = -1009999999999

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
                "bin_channel": "",
                "tutorial_link": "",
                "fsub": {"status": False, "channel": ""},
                "sh1": {"status": False, "domain": "", "api": ""},
                "sh2": {"status": False, "domain": "", "api": ""},
                "sh3": {"status": False, "domain": "", "api": ""},
                "sh4": {"status": False, "domain": "", "api": ""},
            }
            await self.settings.insert_one(default)
            return default
            
        if isinstance(data.get("fsub"), bool):
            new_fsub = {"status": data["fsub"], "channel": ""}
            await self.settings.update_one({"id": "config"}, {"$set": {"fsub": new_fsub}}, upsert=True)
            data["fsub"] = new_fsub
            
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
            db_settings = await self.get_db_settings()
            bin_channel = db_settings.get("bin_channel")
            
            if not bin_channel:
                return web.Response(status=404)

            file_msg = await self.get_messages(bin_channel, msg_id)
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
            db_settings = await self.get_db_settings()
            bin_channel = db_settings.get("bin_channel")
            
            if not bin_channel:
                return web.Response(text="Bin channel is not configured.", status=500)

            file_msg = await self.get_messages(bin_channel, msg_id)
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

            share_url = f"{self.public_url}/watch/{msg_id}"
            sh_num = request.query.get("sh")
            if sh_num and sh_num.isdigit():
                sh_data = db_settings.get(f"sh{sh_num}")
                if sh_data and sh_data.get("status"):
                    target_raw = f"{self.public_url}/watch/{msg_id}"
                    share_url = await self.get_shortlink(target_raw, sh_data['domain'], sh_data['api'])

            html_content = tv_template_sheffy_samra.replace("[[STREAM_URL]]", stream_url)
            html_content = html_content.replace("[[DOWNLOAD_URL]]", download_url)
            html_content = html_content.replace("[[THUMB_URL]]", thumb_url)
            html_content = html_content.replace("[[FILE_NAME]]", file_name)
            html_content = html_content.replace("[[MIME_TYPE]]", mime_type)
            html_content = html_content.replace("[[SHARE_URL]]", share_url)

            return web.Response(text=html_content, content_type='text/html')
        except Exception as e:
            logger.error(f"Watch handler error: {e}")
            return web.HTTPInternalServerError()

    async def stream_handler(self, request):
        try:
            msg_id = int(request.match_info['msg_id'])
            db_settings = await self.get_db_settings()
            bin_channel = db_settings.get("bin_channel")
            
            if not bin_channel:
                return web.Response(status=500, text="Bin channel is not configured.")

            file_msg = await self.get_messages(bin_channel, msg_id)
            
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

@bot.on_message(filters.command(["sbinch"]) & filters.user(Config.OWNER_ID))
async def set_bin_channel(c, m: Message):
    if len(m.command) < 2:
        return await m.reply("<b>Usage:</b> <code>/sbinch -100123456789</code>\nOr use username: <code>/sbinch @mybinchannel</code>", parse_mode=enums.ParseMode.HTML)
    
    try:
        channel = int(m.command[1])
    except ValueError:
        channel = m.command[1]
        
    try:
        await c.settings.update_one({"id": "config"}, {"$set": {"bin_channel": channel}}, upsert=True)
        await m.reply(f"✅ <b>Success!</b> Bin Channel ID <b>{channel}</b> is saved in MongoDB.", parse_mode=enums.ParseMode.HTML)
    except Exception as e:
        await m.reply(f"❌ <b>Error saving channel:</b>\n<code>{e}</code>", parse_mode=enums.ParseMode.HTML)

@bot.on_message(filters.command(["sett"]) & filters.user(Config.OWNER_ID))
async def set_tutorial_link(c, m: Message):
    admin_states[m.from_user.id] = {"step": "tutorial_link"}
    await m.reply("🟢 <b>How to Download Link Setup</b>\n\n👉 Please send the <b>URL/Link</b> (or send 'off' to remove):", parse_mode=enums.ParseMode.HTML)

@bot.on_message(filters.command(["forcesub"]) & filters.user(Config.OWNER_ID))
async def toggle_fsub(c, m: Message):
    if len(m.command) < 2 or m.command[1].lower() not in ["on", "off"]:
        return await m.reply("<b>Usage:</b> <code>/forcesub on</code> or <code>/forcesub off</code>", parse_mode=enums.ParseMode.HTML)
        
    state = m.command[1].lower()
    
    if state == "off":
        await c.settings.update_one({"id": "config"}, {"$set": {"fsub.status": False}}, upsert=True)
        if m.from_user.id in admin_states:
            del admin_states[m.from_user.id]
        await m.reply("✅ <b>Force Subscribe has been turned OFF.</b>", parse_mode=enums.ParseMode.HTML)
        
    elif state == "on":
        admin_states[m.from_user.id] = {"step": "fsub_channel"}
        await m.reply("🟢 <b>Force Subscribe Setup</b>\n\n👉 Please send the <b>Channel ID</b> (e.g., <code>-100123456789</code>) or <b>Username</b> (e.g., <code>@mychannel</code>):", parse_mode=enums.ParseMode.HTML)

@bot.on_message(filters.command(["setsh1st", "setsh2nd", "setsh3rd", "setsh4th"]) & filters.user(Config.OWNER_ID))
async def setup_shorteners(c, m: Message):
    cmd = m.command[0].lower()
    num = cmd[5:6] 
    
    if len(m.command) < 2:
        return await m.reply(f"<b>Usage:</b> <code>/{cmd} on</code> or <code>/{cmd} off</code>", parse_mode=enums.ParseMode.HTML)
        
    state = m.command[1].lower()
    
    if state == "off":
        await c.settings.update_one({"id": "config"}, {"$set": {f"sh{num}.status": False}}, upsert=True)
        if m.from_user.id in admin_states:
            del admin_states[m.from_user.id]
        await m.reply(f"✅ <b>Shortener {num}</b> has been turned <b>OFF</b>.", parse_mode=enums.ParseMode.HTML)
        
    elif state == "on":
        admin_states[m.from_user.id] = {"step": "domain", "num": num}
        await m.reply(f"🟢 <b>Setting up Shortener {num}</b>\n\n👉 Please send the <b>DOMAIN NAME</b> (e.g., <code>shareus.io</code>):", parse_mode=enums.ParseMode.HTML)

@bot.on_message(filters.private & filters.text & filters.user(Config.OWNER_ID) & ~filters.command(["start", "smdetails", "forcesub", "setsh1st", "setsh2nd", "setsh3rd", "setsh4th", "sbinch", "sett"]))
async def state_handler(c, m: Message):
    user_id = m.from_user.id
    
    if user_id in admin_states:
        state_info = admin_states[user_id]
        step = state_info["step"]
        
        if step == "tutorial_link":
            link = m.text.strip()
            if link.lower() in ["off", "none", "disable"]:
                await c.settings.update_one({"id": "config"}, {"$set": {"tutorial_link": ""}}, upsert=True)
                del admin_states[user_id]
                return await m.reply("✅ <b>Tutorial link removed. Button will be hidden.</b>", parse_mode=enums.ParseMode.HTML)
            
            if not link.startswith("http"):
                link = "https://" + link
                
            await c.settings.update_one({"id": "config"}, {"$set": {"tutorial_link": link}}, upsert=True)
            del admin_states[user_id]
            await m.reply(f"✅ <b>Success!</b> 'How to Download' link saved:\n<code>{link}</code>", parse_mode=enums.ParseMode.HTML)
            return
            
        if step == "fsub_channel":
            channel = m.text.strip()
            processing = await m.reply("<i>Verifying admin rights...</i>", parse_mode=enums.ParseMode.HTML)
            try:
                member = await c.get_chat_member(channel, c.me.id)
                if member.status not in [enums.ChatMemberStatus.ADMINISTRATOR, enums.ChatMemberStatus.OWNER]:
                    return await processing.edit("❌ <b>Error:</b> I am not an admin in that channel.")
                
                chat = await c.get_chat(channel)
                await c.settings.update_one({"id": "config"}, {"$set": {"fsub.status": True, "fsub.channel": channel}}, upsert=True)
                del admin_states[user_id]
                await processing.edit(f"✅ <b>Success!</b> Force Subscribe is now strictly <b>ON</b> for <b>{chat.title or channel}</b>.", parse_mode=enums.ParseMode.HTML)
            except Exception as e:
                await processing.edit(f"❌ <b>Verification Failed.</b> Ensure bot is Admin.\n<code>{e}</code>", parse_mode=enums.ParseMode.HTML)
            return

        num = state_info.get("num")
        if step == "domain":
            domain = m.text.strip()
            await c.settings.update_one({"id": "config"}, {"$set": {f"sh{num}.domain": domain}}, upsert=True)
            admin_states[user_id]["step"] = "api"
            await m.reply(f"✅ <b>Domain saved:</b> <code>{domain}</code>\n\n👉 Now, please send the <b>API KEY</b>:", parse_mode=enums.ParseMode.HTML)
        
        elif step == "api":
            api = m.text.strip()
            await c.settings.update_one({"id": "config"}, {"$set": {f"sh{num}.api": api, f"sh{num}.status": True}}, upsert=True)
            del admin_states[user_id]
            await m.reply(f"✅ <b>API saved. Shortener {num} is ON.</b>", parse_mode=enums.ParseMode.HTML)

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
    
    bin_ch = db.get('bin_channel')
    text += f"📂 <b>Bin Channel:</b> <code>{bin_ch if bin_ch else 'NOT SET'}</code>\n"
    
    tut_link = db.get('tutorial_link')
    text += f"❓ <b>Tutorial Link:</b> <code>{tut_link if tut_link else 'NOT SET'}</code>\n\n"
    
    text += f"🔗 <b>Shorteners Status:</b>\n\n"
    for i in range(1, 5):
        sh = db.get(f'sh{i}', {})
        status = "✅ <b>ON</b>" if sh.get('status') else "❌ <b>OFF</b>"
        domain = sh.get('domain') if sh.get('domain') else 'Not Set'
        api = sh.get('api') if sh.get('api') else 'Not Set'
        text += f"<b>Shortener {i}:</b> {status}\n"
        text += f" ├ <b>Domain:</b> <code>{domain}</code>\n"
        text += f" └ <b>API:</b> <code>{api}</code>\n\n"
        
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
    
    db = await c.get_db_settings()
    fsub_conf = db.get("fsub", {})
    buttons = []
    
    buttons.append([InlineKeyboardButton("📢 Updates Channel", url="https://t.me/kamai4youpayment")])
    
    if fsub_conf.get("status") and fsub_conf.get("channel"):
        try:
            chat = await c.get_chat(fsub_conf["channel"])
            invite_link = chat.invite_link or f"https://t.me/{str(fsub_conf['channel']).replace('@', '')}"
            buttons.append([InlineKeyboardButton("🔗 Join Force Sub Channel", url=invite_link)])
        except Exception:
            pass
            
    await m.reply_text(
        text,
        reply_markup=InlineKeyboardMarkup(buttons) if buttons else None,
        parse_mode=enums.ParseMode.HTML
    )

@bot.on_message(filters.private & (filters.document | filters.video | filters.audio))
async def handle_file(c: StreamBot, m: Message):
    db = await c.get_db_settings()
    
    fsub_conf = db.get("fsub", {})
    if fsub_conf.get("status") and fsub_conf.get("channel"):
        channel = fsub_conf["channel"]
        try:
            await c.get_chat_member(channel, m.from_user.id)
        except errors.UserNotParticipant:
            chat = await c.get_chat(channel)
            invite_link = chat.invite_link or f"https://t.me/{str(channel).replace('@', '')}"
            return await m.reply(
                "<blockquote>❌ <b>Join Channel First!</b>\n\nYou must strictly join our channel to process and stream files.</blockquote>",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔗 Join Channel Now", url=invite_link)]]),
                parse_mode=enums.ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Fsub Check Error: {e}")

    bin_channel = db.get("bin_channel")
    if not bin_channel:
        return await m.reply("❌ <b>Bin Channel not set!</b> Admin needs to configure it via <code>/sbinch</code>.", parse_mode=enums.ParseMode.HTML)

    processing_msg = await m.reply("<i>Processing your file...</i>", parse_mode=enums.ParseMode.HTML)

    try:
        bin_msg = await m.forward(bin_channel)
    except Exception as e:
        logger.error(f"Forwarding Error: {e}")
        return await processing_msg.edit(f"❌ <b>Error:</b> Failed to forward file. Verify Bin Channel is set and bot is Admin in the channel.\n<code>{e}</code>", parse_mode=enums.ParseMode.HTML)
    
    watch_url = f"{c.public_url}/watch/{bin_msg.id}"
    download_url = f"{c.public_url}/download/{bin_msg.id}"
    
    file = m.document or m.video or m.audio
    file_name = getattr(file, 'file_name', None) or f"File_{bin_msg.id}"
    
    text = f"<blockquote>📁 <b>File Name:</b> <code>{file_name}</code>\n\n"
    text += f"📺 <b>Raw Watch Link:</b>\n👉 <code>{watch_url}</code>\n\n"
    text += f"📥 <b>Raw Download Link:</b>\n👉 <code>{download_url}</code></blockquote>\n\n"
    
    buttons = []
    shorteners_used = False
    
    for i in range(1, 5):
        sh = db.get(f'sh{i}', {})
        if sh.get('status') and sh.get('domain') and sh.get('api'):
            shorteners_used = True
            btn_text = f"🔗 Share via {sh['domain'].split('.')[0].title()}"
            buttons.append([InlineKeyboardButton(btn_text, callback_data=f"sh_{i}_{bin_msg.id}")])
            
    if shorteners_used:
        text += "<i>👇 Tap any shortener below to generate a share post:</i>"
    else:
        text += "<i>✅ Processed directly as no shorteners are active.</i>"
        buttons.append([InlineKeyboardButton("▶️ Watch Online", url=watch_url)])
        buttons.append([InlineKeyboardButton("📥 Fast Download", url=download_url)])
    
    await processing_msg.delete()
    await m.reply_text(
        text, 
        reply_markup=InlineKeyboardMarkup(buttons) if buttons else None, 
        quote=True, 
        disable_web_page_preview=True,
        parse_mode=enums.ParseMode.HTML
    )

@bot.on_callback_query(filters.regex(r"^sh_(\d+)_(\d+)$"))
async def shortener_callback_handler(c: StreamBot, cb):
    await cb.answer("Generating post... Please wait.", show_alert=False)
    
    sh_num = cb.matches[0].group(1)
    msg_id = int(cb.matches[0].group(2))
    
    db = await c.get_db_settings()
    sh_data = db.get(f"sh{sh_num}", {})
    
    if not sh_data or not sh_data.get("status"):
        return await cb.answer("❌ This shortener is disabled.", show_alert=True)
        
    watch_url = f"{c.public_url}/watch/{msg_id}?sh={sh_num}"
    short_watch_url = await c.get_shortlink(watch_url, sh_data.get('domain', ''), sh_data.get('api', ''))
    
    raw_download_url = f"{c.public_url}/download/{msg_id}"
    short_download_url = await c.get_shortlink(raw_download_url, sh_data.get('domain', ''), sh_data.get('api', ''))
    
    bin_channel = db.get("bin_channel")
    if not bin_channel:
        return await cb.answer("❌ Bin Channel not set.", show_alert=True)

    try:
        file_msg = await c.get_messages(bin_channel, msg_id)
    except Exception as e:
        logger.error(f"Message Fetch Error: {e}")
        return await cb.message.reply_text(f"❌ <b>Error:</b> Failed to fetch file.\n<code>{e}</code>", parse_mode=enums.ParseMode.HTML)
        
    file = file_msg.document or file_msg.video or file_msg.audio
    file_name = getattr(file, 'file_name', None) or f"File_{msg_id}"
    
    caption_text = f"<blockquote>🎥 <b>Title:</b> <code>{file_name}</code>\n\n"
    caption_text += f"📺 <b>Watch Link:</b>\n👉 <code>{short_watch_url}</code>\n\n"
    caption_text += f"📥 <b>Download Link (Tap to copy):</b>\n👉 <code>{short_download_url}</code></blockquote>"
    
    buttons = [
        [InlineKeyboardButton("▶️ Watch Now", url=short_watch_url)],
        [InlineKeyboardButton("📥 Fast Download", url=short_download_url)],
        [InlineKeyboardButton("📤 Share Link", url=f"https://t.me/share/url?url={short_watch_url}")]
    ]
    
    tutorial_link = db.get("tutorial_link", "")
    if tutorial_link:
        buttons.append([InlineKeyboardButton("❓ How to Download", url=tutorial_link)])
    
    await cb.message.reply_text(
        caption_text, 
        reply_markup=InlineKeyboardMarkup(buttons), 
        disable_web_page_preview=True,
        parse_mode=enums.ParseMode.HTML
    )

async def start_services():
    logger.info("Starting Pyrogram Client...")
    await bot.start()
    
    logger.info("Setting Bot Commands Menu...")
    try:
        await bot.delete_bot_commands()
        await bot.set_bot_commands([
            BotCommand("start", "🚀 Start The Stream Bot"),
            BotCommand("smdetails", "📊 System & Bot Stats"),
            BotCommand("sbinch", "⚙️ Setup Bin Channel"),
            BotCommand("sett", "🛠 Setup How to Download Link"),
            BotCommand("forcesub", "🔐 Setup Force Sub Channel"),
            BotCommand("setsh1st", "🟡 Config 1st Shortener"),
            BotCommand("setsh2nd", "🟢 Config 2nd Shortener"),
            BotCommand("setsh3rd", "🔵 Config 3rd Shortener"),
            BotCommand("setsh4th", "🟣 Config 4th Shortener")
        ], scope=BotCommandScopeDefault())
        logger.info("Commands menu wiped and updated successfully!")
    except Exception as e:
        logger.error(f"Failed to set bot commands: {e}")
    
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
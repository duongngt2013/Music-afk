import os
import threading
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord.ext import commands
import yt_dlp

# --- 1. HTTP SERVER NHỎ ĐỂ GIỮ RENDER LUÔN "ALIVE" ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Music Bot is online 24/7!")

def run_http_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

# Chạy ngầm HTTP server
threading.Thread(target=run_http_server, daemon=True).start()

# --- 2. CẤU HÌNH YTDL & FFMPEG (Né chặn bot bằng client TV/iOS) ---
ytdl_format_options = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'default_search': 'scsearch',
    'source_address': '0.0.0.0',
    'extractor_args': {'youtube': {'player_client': ['tv', 'ios', 'web']}}
}

ffmpeg_options = {
    'options': '-vn'
}

ytdl = yt_dlp.YoutubeDL(ytdl_format_options)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')
        self.url = data.get('url')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **ffmpeg_options), data=data)

# --- 3. KHỞI TẠO BOT DISCORD ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Đã đăng nhập thành công dưới tên: {bot.user}")

# Lệnh phát nhạc: !play <tên bài hát hoặc link>
@bot.command(name='play', help='Phát nhạc từ YouTube')
async def play(ctx, *, query):
    if not ctx.author.voice:
        await ctx.send("Bạn phải vào một phòng thoại (voice channel) trước đã nhé!")
        return

    channel = ctx.author.voice.channel
    if ctx.voice_client is None:
        await channel.connect()
    elif ctx.voice_client.channel != channel:
        await ctx.voice_client.move_to(channel)

    async with ctx.typing():
        try:
            player = await YTDLSource.from_url(query, loop=bot.loop, stream=True)
            ctx.voice_client.play(player, after=lambda e: print(f'Lỗi âm thanh: {e}') if e else None)
            await ctx.send(f"🎶 Đang phát: **{player.title}**")
        except Exception as e:
            await ctx.send(f"Đã xảy ra lỗi khi tải bài hát: {e}")

# Lệnh dừng bot: !stop hoặc !leave
@bot.command(name='stop', help='Dừng nhạc và đuổi bot ra khỏi phòng')
async def stop(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("👋 Đã ngắt kết nối khỏi phòng thoại.")
    else:
        await ctx.send("Bot không có trong phòng thoại nào cả!")

# Chạy bot bằng biến môi trường bảo mật trên Render
bot.run(os.getenv('DISCORD_TOKEN'))

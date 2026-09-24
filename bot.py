import discord
from discord.ext import commands
import yt_dlp
import asyncio
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler

# Máy chủ web ảo giữ bot luôn thức trên Cloud
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Music Bot is running 24/7!")

def run_server():
    server = HTTPServer(('0.0.0.0', 8000), SimpleHandler)
    server.serve_forever()

threading.Thread(target=run_server, daemon=True).start()

# Cấu hình Bot Discord
intents = discord.Intents.default()
intents.message_content = True

bot = commands.Bot(command_prefix='!', intents=intents)

YTDL_OPTIONS = {
    'format': 'bestaudio/best',
    'extractaudio': True,
    'audioformat': 'mp3',
    'noplaylist': True,
    'nocheckcertificate': True,
    'quiet': True,
    'default_search': 'auto',
}

FFMPEG_OPTIONS = {
    'before_options': '-reconnect 1 -reconnect_streamed 1 -reconnect_delay_max 5',
    'options': '-vn',
}

ytdl = yt_dlp.YoutubeDL(YTDL_OPTIONS)

class YTDLSource(discord.PCMVolumeTransformer):
    def __init__(self, source, *, data, volume=0.5):
        super().__init__(source, volume)
        self.data = data
        self.title = data.get('title')

    @classmethod
    async def from_url(cls, url, *, loop=None, stream=True):
        loop = loop or asyncio.get_event_loop()
        data = await loop.run_in_executor(None, lambda: ytdl.extract_info(url, download=not stream))
        if 'entries' in data:
            data = data['entries'][0]
        filename = data['url'] if stream else ytdl.prepare_filename(data)
        return cls(discord.FFmpegPCMAudio(filename, **FFMPEG_OPTIONS), data=data)

@bot.event
async def on_ready():
    print(f'Bot nhạc {bot.user} đã hoạt động trên Koyeb!')

@bot.command(name='play')
async def play(ctx, *, url):
    if not ctx.author.voice:
        await ctx.send("⚠️ Bạn phải vào Voice Channel trước!")
        return
    channel = ctx.author.voice.channel
    if ctx.voice_client is None:
        await channel.connect()
    elif ctx.voice_client.channel != channel:
        await ctx.voice_client.move_to(channel)
    async with ctx.typing():
        try:
            player = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
            ctx.voice_client.play(player, after=lambda e: print(f'Lỗi: {e}') if e else None)
            await ctx.send(f'🎵 Đang phát: **{player.title}**')
        except Exception as e:
            await ctx.send(f"❌ Không thể phát link này: {e}")

@bot.command(name='stop')
async def stop(ctx):
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("👋 Đã ngắt kết nối!")

# Token của bạn
bot.run('MTU1MjU4Mjc1Mzg2ODg0NTEwNg.GBtZ4Y.Vgb4eoiR0EGRbzCBRqxGUz82lqyJKJ-8KL6vBQ')

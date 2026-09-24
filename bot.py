import os
import threading
import asyncio
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord.ext import commands
import yt_dlp

# --- 1. HTTP SERVER GIỮ RENDER LUÔN SỐNG 24/7 ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Music Bot 24/7 is online!")

def run_http_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

threading.Thread(target=run_http_server, daemon=True).start()

# --- 2. CẤU HÌNH YTDL & FFMPEG (Dùng SoundCloud né YouTube) ---
ytdl_format_options = {
    'format': 'bestaudio/best',
    'noplaylist': True,
    'default_search': 'scsearch',
    'source_address': '0.0.0.0',
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

# --- 3. QUẢN LÝ HÀNG ĐỢI & AUTOPLAY ---
class MusicPlayer:
    def __init__(self):
        self.queue = []
        self.current = None
        self.autoplay = True # Mặc định bật sẵn Autoplay

guild_players = {}

def get_player(guild_id):
    if guild_id not in guild_players:
        guild_players[guild_id] = MusicPlayer()
    return guild_players[guild_id]

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Bot đã sẵn sàng: {bot.user}")

async def play_next(ctx):
    player = get_player(ctx.guild.id)
    if len(player.queue) > 0:
        player.current = player.queue.pop(0)
        url = player.current['url']
        title = player.current['title']
        
        try:
            source = await YTDLSource.from_url(url, loop=bot.loop, stream=True)
            def after_playing(error):
                if error:
                    print(f"Lỗi âm thanh: {error}")
                fut = asyncio.run_coroutine_threadsafe(play_next(ctx), bot.loop)
                try:
                    fut.result()
                except Exception as e:
                    print(e)

            ctx.voice_client.play(source, after=after_playing)
            await ctx.send(f"🎶 Đang phát: **{title}**")
        except Exception as e:
            await ctx.send(f"Lỗi khi phát bài: {e}")
            await play_next(ctx)
    else:
        player.current = None
        if player.autoplay:
            # Tự động tìm bài nhạc chill/lofi tiếp theo khi hết hàng đợi
            try:
                data = await bot.loop.run_in_executor(None, lambda: ytdl.extract_info("scsearch:Lofi Chill Remix", download=False))
                if 'entries' in data and len(data['entries']) > 0:
                    entry = data['entries'][0]
                    player.queue.append({'url': entry.get('webpage_url') or entry.get('url'), 'title': entry['title']})
                    await play_next(ctx)
            except Exception as e:
                print(f"Lỗi Autoplay: {e}")
        else:
            await ctx.send("🏁 Hết nhạc trong hàng đợi rồi! Bot vẫn ở đây chờ lệnh nhé.")

# --- 4. CÁC LỆNH CỦA BOT ---
@bot.command(name='play', help='Phát nhạc hoặc thêm vào hàng đợi')
async def play(ctx, *, query):
    if not ctx.author.voice:
        await ctx.send("Bạn phải vào phòng voice trước đã nhé!")
        return

    channel = ctx.author.voice.channel
    if ctx.voice_client is None:
        await channel.connect()
    elif ctx.voice_client.channel != channel:
        await ctx.voice_client.move_to(channel)

    async with ctx.typing():
        try:
            data = await bot.loop.run_in_executor(None, lambda: ytdl.extract_info(query, download=False))
            if 'entries' in data:
                info = data['entries'][0]
            else:
                info = data
            
            song = {
                'url': info.get('webpage_url') or info.get('url'),
                'title': info.get('title')
            }

            player = get_player(ctx.guild.id)
            player.queue.append(song)
            await ctx.send(f"➕ Đã thêm vào hàng đợi: **{song['title']}**")

            if not ctx.voice_client.is_playing() and player.current is None:
                await play_next(ctx)
        except Exception as e:
            await ctx.send(f"Không tìm thấy bài hát: {e}")

@bot.command(name='skip', help='Bỏ qua bài hiện tại')
async def skip(ctx):
    if ctx.voice_client and ctx.voice_client.is_playing():
        ctx.voice_client.stop()
        await ctx.send("⏭️ Đã chuyển sang bài tiếp theo!")
    else:
        await ctx.send("Bot có đang phát bài nào đâu mà skip!")

@bot.command(name='queue', aliases=['q'], help='Xem danh sách hàng đợi')
async def show_queue(ctx):
    player = get_player(ctx.guild.id)
    if not player.queue and not player.current:
        await ctx.send("Hàng đợi đang trống trơn!")
        return
    
    msg = f"🎵 **Đang phát:** {player.current['title'] if player.current else 'Không có'}\n\n**Danh sách chờ tiếp theo:**\n"
    for i, song in enumerate(player.queue[:10], 1):
        msg += f"{i}. {song['title']}\n"
    await ctx.send(msg)

@bot.command(name='autoplay', help='Bật/tắt chế độ tự động phát nhạc')
async def toggle_autoplay(ctx):
    player = get_player(ctx.guild.id)
    player.autoplay = not player.autoplay
    status = "BẬT" if player.autoplay else "TẮT"
    await ctx.send(f"🔄 Đã {status} chế độ Autoplay.")

@bot.command(name='stop', aliases=['leave'], help='Đuổi bot ra khỏi phòng')
async def stop(ctx):
    player = get_player(ctx.guild.id)
    player.queue.clear()
    player.current = None
    if ctx.voice_client:
        await ctx.voice_client.disconnect()
        await ctx.send("👋 Đã rời phòng thoại và xóa hàng đợi.")

bot.run(os.getenv('DISCORD_TOKEN'))

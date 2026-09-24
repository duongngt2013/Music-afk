import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
import discord
from discord.ext import commands

# --- HTTP SERVER NHỎ ĐỂ GIỮ RENDER LUÔN "ALIVE" ---
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Music AFK Bot is running!")

def run_http_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

# Chạy HTTP server ngầm
threading.Thread(target=run_http_server, daemon=True).start()

# --- CODE BOT DISCORD CỦA BẠN ---
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

# Chạy bot bằng biến môi trường bảo mật
bot.run(os.getenv('DISCORD_TOKEN'))

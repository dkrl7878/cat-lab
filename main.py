import discord
from discord.ext import commands
import os
import aiohttp
import asyncio
from datetime import datetime
import pytz

TOKEN = os.getenv("DISCORD_TOKEN")  # 환경변수에서 토큰 읽기
CHANNEL_ID = int(os.getenv("MONITOR_CHANNEL_ID"))  # 감시 채널 ID

intents = discord.Intents.default()
intents.voice_states = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    print(f"{bot.user} 봇이 켜졌습니다.")

@bot.event
async def on_voice_state_update(member, before, after):
    if before.channel != after.channel:
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            await channel.send(f"{member.display_name}님이 음성 채널을 이동했습니다.")

# Health check용 웹 서버
from aiohttp import web

async def handle(request):
    return web.Response(text="OK")

async def start_webserver():
    app = web.Application()
    app.router.add_get('/health', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8000)
    await site.start()

async def self_ping():
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                await session.get("http://localhost:8000/health")
        except Exception as e:
            print("Self ping 실패:", e)
        await asyncio.sleep(180)

async def main():
    await start_webserver()
    await asyncio.gather(
        self_ping(),
        bot.start(TOKEN)
    )

asyncio.run(main())

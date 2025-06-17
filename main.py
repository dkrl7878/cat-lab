import discord
import os
from keep_alive import keep_alive  # 추가

TOKEN = os.getenv("DISCORD_TOKEN")

intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True

bot = discord.Bot(intents=intents)

@bot.event
async def on_ready():
    print(f"✅ 봇 로그인 완료: {bot.user}")

@bot.slash_command(name="ping", description="핑 확인")
async def ping(ctx):
    await ctx.respond("퐁!")

keep_alive()  # 여기에 추가
bot.run(TOKEN)

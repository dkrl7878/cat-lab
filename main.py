import discord
import os

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

bot.run(TOKEN)

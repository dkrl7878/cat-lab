import os
import discord
from discord.ext import commands # commands 모듈을 임포트합니다.
import aiohttp
import asyncio

# 환경 변수에서 디스코드 봇 토큰을 읽어옵니다.
TOKEN = os.getenv("DISCORD_TOKEN")

# 봇의 인텐트 설정. 슬래시 명령어를 사용하더라도 특정 기능에 인텐트가 필요할 수 있습니다.
# 'MESSAGE CONTENT INTENT'는 일반 메시지 이벤트를 처리할 때 필요하며,
# 슬래시 명령어는 기본적으로 메시지 내용을 직접 읽는 방식이 아니므로 필수는 아니지만,
# 다른 메시지 기반 기능을 추가할 경우를 대비해 켜두는 경우가 많습니다.
intents = discord.Intents.default()
intents.message_content = True # 메시지 내용을 읽어야 하는 경우 활성화 (디스코드 개발자 포털에서도 활성화 필요)
intents.members = True # 길드 멤버 정보가 필요한 경우 활성화 (디스코드 개발자 포털에서도 활성화 필요)


# commands.Bot을 사용하여 봇 객체를 생성합니다.
# command_prefix는 메시지 기반 명령어를 사용할 때 필요하지만,
# 슬래시 명령어만 사용할 경우 크게 중요하지 않습니다. 하지만 인수로 넣어줘야 합니다.
bot = commands.Bot(command_prefix="!", intents=intents)

# 봇이 디스코드에 성공적으로 연결되었을 때 실행되는 이벤트입니다.
@bot.event
async def on_ready():
    print(f"[{bot.user}] 봇이 성공적으로 켜졌습니다.")
    print("슬래시 명령어 '/안녕'과 헬스 체크 기능이 활성화되었습니다.")
    print("슬래시 명령어를 디스코드에 동기화합니다...")
    try:
        # 슬래시 명령어를 디스코드에 등록(동기화)합니다.
        # 길드 ID를 지정하면 특정 서버에만 빠르게 동기화되고,
        # 지정하지 않으면 모든 서버에 전역적으로 동기화됩니다(최대 1시간 소요).
        # GUILD_ID = int(os.getenv("YOUR_GUILD_ID")) # 특정 서버에만 동기화하려면 이 주석을 풀고, 환경변수에 길드 ID 설정
        # await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        await bot.tree.sync() # 모든 서버에 동기화
        print("슬래시 명령어 동기화 완료.")
    except Exception as e:
        print(f"슬래시 명령어 동기화 실패: {e}")

# --- 슬래시 명령어 정의 ---
# '/안녕' 명령어를 정의합니다.
@bot.tree.command(name="안녕", description="봇이 안녕하세요! 반갑습니다. 라고 인사합니다.")
async def hello_command(interaction: discord.Interaction):
    """봇이 안녕하세요! 반갑습니다. 라고 인사합니다."""
    await interaction.response.send_message("안녕하세요! 반갑습니다.")

# --- Health check용 웹 서버 및 self-ping 기능 ---

from aiohttp import web

async def handle_health_check(request):
    return web.Response(text="OK")

async def start_webserver():
    app = web.Application()
    app.router.add_get('/health', handle_health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8000)
    await site.start()
    print("Health check 웹 서버가 http://0.0.0.0:8000/health 에서 시작되었습니다.")

async def self_ping():
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                await session.get("http://localhost:8000/health")
        except Exception as e:
            print(f"Self ping 실패: {e}")
        await asyncio.sleep(180)

async def main():
    await start_webserver()
    await asyncio.gather(
        self_ping(),
        bot.start(TOKEN)
    )

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("봇이 수동으로 종료되었습니다.")
    except Exception as e:
        print(f"예상치 못한 오류 발생: {e}")

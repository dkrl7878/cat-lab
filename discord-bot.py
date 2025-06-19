import os
import discord
from discord.ext import commands
from discord import app_commands # 슬래시 명령어를 위해 app_commands 모듈 임포트
import aiohttp
import asyncio
from datetime import datetime # 날짜/시간 처리를 위해 임포트

# --- 환경 변수 설정 ---
TOKEN = os.getenv("DISCORD_TOKEN") # 디스코드 봇 토큰
FORUM_CHANNEL_ID = int(os.getenv("FORUM_CHANNEL_ID")) # 메시지를 보낼 포럼 채널의 ID

# --- 봇 인텐트 설정 ---
# 슬래시 명령어를 사용하더라도 특정 기능에 인텐트가 필요할 수 있습니다.
intents = discord.Intents.default()
intents.message_content = True # 일반 메시지 내용을 읽는 데 필요 (개발자 포털에서도 활성화 필요)
intents.members = True       # 길드 멤버 정보가 필요한 경우 활성화 (개발자 포털에서도 활성화 필요)

# commands.Bot을 사용하여 봇 객체를 생성합니다.
# command_prefix는 메시지 기반 명령어를 사용할 때 필요하며, 슬래시 명령어만 사용할 경우 크게 중요하지 않습니다.
bot = commands.Bot(command_prefix="!", intents=intents)

# 봇이 디스코드에 성공적으로 연결되었을 때 실행되는 이벤트입니다.
@bot.event
async def on_ready():
    print(f"[{bot.user}] 봇이 성공적으로 켜졌습니다.")
    print("슬래시 명령어 '/레이드생성'과 헬스 체크 기능이 활성화되었습니다.")
    print("슬래시 명령어를 디스코드에 동기화합니다...")
    try:
        # 슬래시 명령어를 디스코드에 등록(동기화)합니다.
        # 모든 서버에 전역적으로 동기화하는 경우 최대 1시간 소요될 수 있습니다.
        # 특정 서버(길드)에만 빠르게 동기화하려면 GUILD_ID를 지정할 수 있습니다.
        # GUILD_ID = int(os.getenv("YOUR_GUILD_ID")) # 예시: 특정 길드 ID 환경변수 사용
        # await bot.tree.sync(guild=discord.Object(id=GUILD_ID))
        await bot.tree.sync() # 모든 서버에 동기화
        print("슬래시 명령어 동기화 완료.")
    except Exception as e:
        print(f"슬래시 명령어 동기화 실패: {e}")

# --- 슬래시 명령어 정의: '/레이드생성' ---
@bot.tree.command(name="레이드생성", description="로스트아크 레이드 모집 글을 포럼 채널에 올립니다.")
@app_commands.describe(
    월="레이드를 진행할 월 (예: 6)",
    일="레이드를 진행할 일 (예: 20)",
    시간="레이드를 진행할 시간 (24시간 형식, 예: 2130)",
    레이드종류="모집할 로스트아크 레이드 종류",
    숙련도="요구하는 숙련도"
)
@app_commands.choices(
    레이드종류=[
        app_commands.Choice(name="카멘 노말", value="카멘_노말"),
        app_commands.Choice(name="카멘 하드", value="카멘_하드"),
        app_commands.Choice(name="상아탑 노말", value="상아탑_노말"),
        app_commands.Choice(name="상아탑 하드", value="상아탑_하드"),
        app_commands.Choice(name="카양겔 노말", value="카양겔_노말"),
        app_commands.Choice(name="카양겔 하드", value="카양겔_하드"),
        app_commands.Choice(name="아브렐슈드", value="아브렐슈드"),
        app_commands.Choice(name="일리아칸 노말", value="일리아칸_노말"),
        app_commands.Choice(name="일리아칸 하드", value="일리아칸_하드"),
        app_commands.Choice(name="에키드나 노말", value="에키드나_노말"),
        app_commands.Choice(name="에키드나 하드", value="에키드나_하드"),
        app_commands.Choice(name="찬란한 명예의 알현", value="찬란한_명예의_알현"),
        app_commands.Choice(name="혼돈의 상아탑", value="혼돈의_상아탑"),
        app_commands.Choice(name="낙원의 문", value="낙원의_문"),
        app_commands.Choice(name="오레하의 우물", value="오레하의_우물"),
        app_commands.Choice(name="도비스", value="도비스"),
        app_commands.Choice(name="어비스 던전 (선택)", value="어비스_던전_선택"),
        app_commands.Choice(name="각종 가디언 토벌 (선택)", value="가디언_토벌_선택"),
        app_commands.Choice(name="기타 레이드 (직접 입력)", value="기타_레이드"),
    ],
    숙련도=[
        app_commands.Choice(name="미숙", value="미숙"),
        app_commands.Choice(name="반숙", value="반숙"),
        app_commands.Choice(name="숙련", value="숙련"),
        app_commands.Choice(name="절대숙련", value="절대숙련"),
        app_commands.Choice(name="버스가능", value="버스가능"),
    ]
)
async def create_raid(
    interaction: discord.Interaction,
    월: int,
    일: int,
    시간: int, # 24시간 형식 (예: 2130)
    레이드종류: app_commands.Choice[str], # 드롭다운 선택을 위해 app_commands.Choice 사용
    숙련도: app_commands.Choice[str] # 드롭다운 선택을 위해 app_commands.Choice 사용
):
    """로스트아크 레이드 모집 글을 포럼 채널에 올립니다."""

    # 입력 값 유효성 검사 (간단한 예시, 필요에 따라 더 강화할 수 있음)
    current_year = datetime.now().year
    try:
        # 시간 형식을 HHMM에서 HH:MM으로 변환
        time_str = f"{시간 // 100:02d}:{시간 % 100:02d}"
        # 날짜 객체 생성 (유효성 검사 목적)
        datetime(current_year, 월, 일, 시간 // 100, 시간 % 100)
    except ValueError:
        await interaction.response.send_message(
            "날짜 또는 시간 형식이 올바르지 않습니다. 월, 일, 시간(HHMM 형식)을 확인해주세요.",
            ephemeral=True # 이 메시지는 명령어를 사용한 사람에게만 보입니다.
        )
        return

    # 포럼 채널 객체를 가져옵니다.
    forum_channel = bot.get_channel(FORUM_CHANNEL_ID)

    # 채널이 포럼 채널 타입이 아니거나 찾을 수 없는 경우
    if not isinstance(forum_channel, discord.ForumChannel):
        await interaction.response.send_message(
            f"설정된 채널 ID({FORUM_CHANNEL_ID})를 찾을 수 없거나 포럼 채널이 아닙니다. 관리자에게 문의하세요.",
            ephemeral=True
        )
        print(f"오류: 설정된 채널 ID({FORUM_CHANNEL_ID})가 포럼 채널이 아니거나 찾을 수 없습니다.")
        return

    # 레이드 종류 및 숙련도 값 가져오기 (value 속성 사용)
    raid_type_display = 레이드종류.name # 사용자에게 보이는 이름
    proficiency_display = 숙련도.name # 사용자에게 보이는 이름

    # 포럼 게시글 제목 및 내용 구성
    post_title = f"[{raid_type_display}] {월}월 {일}일 {time_str} 레이드 모집 ({proficiency_display})"
    post_content = (
        f"**__레이드 모집 정보__**\n"
        f"**날짜:** {월}월 {일}일\n"
        f"**시간:** {time_str}\n"
        f"**레이드 종류:** {raid_type_display}\n"
        f"**숙련도:** {proficiency_display}\n\n"
        f"✅ 참여를 원하시는 분은 이 게시글에 댓글로 참여 의사를 밝혀주세요!\n"
        f"작성자: {interaction.user.mention}" # 명령어 사용자를 멘션
    )

    try:
        # 포럼 채널에 새 스레드(게시글)를 생성합니다.
        new_thread = await forum_channel.create_thread(
            name=post_title,
            content=post_content,
            auto_archive_duration=1440 # 1440분 = 24시간 후 자동 아카이브 (원하는 시간으로 변경 가능)
        )
        await interaction.response.send_message(
            f"레이드 모집 글이 포럼 채널에 성공적으로 생성되었습니다: {new_thread.mention}",
            ephemeral=False # 모든 사람이 볼 수 있도록 일반 메시지로 보냅니다.
        )
    except discord.Forbidden:
        await interaction.response.send_message(
            "봇이 포럼 채널에 게시글을 작성할 권한이 없습니다. 봇 권한을 확인해주세요.",
            ephemeral=True
        )
        print(f"오류: 봇이 채널 {FORUM_CHANNEL_ID}에 게시글을 작성할 권한이 없습니다.")
    except Exception as e:
        await interaction.response.send_message(
            f"레이드 모집 글 생성 중 오류가 발생했습니다: {e}",
            ephemeral=True
        )
        print(f"레이드 모집 글 생성 중 예상치 못한 오류 발생: {e}")


# --- Health check용 웹 서버 및 self-ping 기능 (기존과 동일) ---

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


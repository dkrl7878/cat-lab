import os
import discord # discord.py 라이브러리
import aiohttp # 비동기 HTTP 요청을 위한 라이브러리
import asyncio # 비동기 프로그래밍을 위한 라이브러리

# 환경 변수에서 디스코드 봇 토큰을 읽어옵니다.
# 코옙(Koyeb) 서비스의 환경 변수에 'DISCORD_TOKEN'을 설정해야 합니다.
TOKEN = os.getenv("DISCORD_TOKEN")

# 봇의 기본 인텐트(Bot이 어떤 이벤트를 수신할지 정의)를 설정합니다.
# `intents.default()`는 대부분의 기본 이벤트를 포함합니다.
# 만약 'GUILD MEMBERS INTENT'나 'MESSAGE CONTENT INTENT' 같은 특권 인텐트를 사용할 계획이라면,
# 디스코드 개발자 포털에서 해당 인텐트를 활성화해야 합니다.
intents = discord.Intents.default()
# intents.message_content = True # 만약 봇이 메시지 내용을 읽어야 한다면 이 줄의 주석을 해제하고, 개발자 포털에서도 활성화해야 합니다.
# intents.members = True # 만약 봇이 길드 멤버 정보를 필요로 한다면 이 줄의 주석을 해제하고, 개발자 포털에서도 활성화해야 합니다.

# 디스코드 클라이언트 객체를 생성합니다.
# 현재는 봇이 아무런 명령어나 이벤트를 처리하지 않으므로, discord.Client를 사용합니다.
# 나중에 명령어를 추가할 때는 'discord.ext.commands.Bot'으로 변경할 수 있습니다.
bot = discord.Client(intents=intents)

# 봇이 디스코드에 성공적으로 연결되었을 때 실행되는 이벤트입니다.
# 현재는 단순히 봇이 켜졌다는 메시지만 출력합니다.
@bot.event
async def on_ready():
    print(f"[{bot.user}] 봇이 성공적으로 켜졌습니다.")
    print("현재 봇은 헬스 체크 기능 외에 아무런 기능이 없습니다.")
    print("원하는 기능을 on_message, on_member_join 등의 이벤트 리스너로 추가해 보세요!")

# --- Health check용 웹 서버 및 self-ping 기능 ---
# Koyeb와 같은 서버리스 환경에서 봇이 유휴 상태로 종료되는 것을 방지하기 위함입니다.

from aiohttp import web # 웹 서버 기능을 제공하는 aiohttp의 하위 모듈

# 헬스 체크 요청을 처리하는 핸들러 함수입니다.
# '/health' 경로로 요청이 오면 'OK' 응답을 반환합니다.
async def handle_health_check(request):
    return web.Response(text="OK")

# 헬스 체크용 웹 서버를 시작하는 함수입니다.
async def start_webserver():
    app = web.Application()
    # '/health' 경로에 handle_health_check 함수를 연결합니다.
    app.router.add_get('/health', handle_health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    # 0.0.0.0의 8000번 포트에서 웹 서버를 시작합니다.
    # Koyeb 환경에서는 이 포트를 사용하도록 설정해야 합니다.
    site = web.TCPSite(runner, '0.0.0.0', 8000)
    await site.start()
    print("Health check 웹 서버가 http://0.0.0.0:8000/health 에서 시작되었습니다.")

# 봇 스스로 헬스 체크 엔드포인트에 주기적으로 핑을 보내는 함수입니다.
# 이를 통해 Koyeb가 봇이 활성 상태임을 인식하고 종료하지 않도록 돕습니다.
async def self_ping():
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                # 봇이 실행되는 동일한 호스트의 헬스 체크 엔드포인트로 요청을 보냅니다.
                await session.get("http://localhost:8000/health")
            # print("Self ping 성공!") # 디버깅 시 필요하면 주석 해제
        except Exception as e:
            print(f"Self ping 실패: {e}")
        # 3분(180초)마다 핑을 보냅니다.
        await asyncio.sleep(180)

# 봇의 메인 진입점 함수입니다.
# 웹 서버 시작과 봇 로그인 및 self-ping을 동시에 실행합니다.
async def main():
    await start_webserver() # 헬스 체크 웹 서버 시작
    # self_ping과 봇 시작을 동시에 비동기적으로 실행합니다.
    await asyncio.gather(
        self_ping(),
        bot.start(TOKEN) # 디스코드 봇 로그인 및 시작
    )

# Python 스크립트가 직접 실행될 때 main 함수를 실행합니다.
if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("봇이 수동으로 종료되었습니다.")
    except Exception as e:
        print(f"예상치 못한 오류 발생: {e}")


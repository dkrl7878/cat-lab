import os
import discord
from discord.ext import commands
from discord import app_commands # 슬래시 명령어를 위해 app_commands 모듈 임포트
import aiohttp
import asyncio
from datetime import datetime # 날짜/시간 처리를 위해 임포트
import re # 참여 명단 파싱을 위한 정규 표현식 모듈 임포트

# --- 환경 변수 설정 ---
TOKEN = os.getenv("DISCORD_TOKEN") # 디스코드 봇 토큰
FORUM_CHANNEL_ID = int(os.getenv("FORUM_CHANNEL_ID")) # 메시지를 보낼 포럼 채널의 ID

# --- 봇 인텐트 설정 ---
# 슬래시 명령어를 사용하더라도 특정 기능에 인텐트가 필요할 수 있습니다.
intents = discord.Intents.default()
intents.message_content = True # 일반 메시지 내용을 읽는 데 필요 (개발자 포털에서도 활성화 필요)
intents.members = True       # 길드 멤버 정보가 필요한 경우 활성화 (개발자 포럼에서도 활성화 필요)

# commands.Bot을 사용하여 봇 객체를 생성합니다.
# command_prefix는 메시지 기반 명령어를 사용할 때 필요하며, 슬래시 명령어만 사용할 경우 크게 중요하지 않습니다.
bot = commands.Bot(command_prefix="!", intents=intents)

# --- 상수 및 선택지 정의 (가독성을 위해) ---
RAID_TYPE_CHOICES = [
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
]

PROFICIENCY_CHOICES = [
    app_commands.Choice(name="미숙", value="미숙"),
    app_commands.Choice(name="반숙", value="반숙"),
    app_commands.Choice(name="숙련", value="숙련"),
    app_commands.Choice(name="절대숙련", value="절대숙련"),
    app_commands.Choice(name="버스가능", value="버스가능"),
]

DEFAULT_MAX_PARTICIPANTS = 8 # 기본 모집 인원 (로스트아크 8인 레이드 기준)

# --- 참여 신청 모달 정의 ---
class RaidSignupModal(discord.ui.Modal, title="참여 신청"):
    """
    '참여 신청' 버튼 클릭 시 나타나는 모달입니다.
    캐릭터 닉네임을 입력받습니다.
    """
    character_name = discord.ui.TextInput(
        label="캐릭터 닉네임",
        placeholder="참여를 원하는 캐릭터 닉네임을 입력하세요.",
        min_length=1, # 최소 1글자
        max_length=50, # 최대 50글자
        required=True
    )

    # 모달을 통해 받은 정보를 바탕으로 원본 메시지를 업데이트하기 위해
    # 원본 메시지 ID와 해당 메시지가 있는 스레드 ID를 초기화 시 받습니다.
    def __init__(self, original_message_id: int, thread_id: int):
        super().__init__()
        self.original_message_id = original_message_id
        self.thread_id = thread_id

    async def on_submit(self, interaction: discord.Interaction):
        # 모달 제출에 대한 즉각적인 응답 (사용자에게 '신청 중...' 표시)
        await interaction.response.send_message("참여 신청 중...", ephemeral=True)

        try:
            # 봇이 메시지를 수정하기 위해 해당 스레드 채널과 원본 메시지를 가져옵니다.
            thread_channel = bot.get_channel(self.thread_id)
            # 채널 타입이 Discord.Thread가 아닐 경우 에러 처리
            if not isinstance(thread_channel, discord.Thread):
                await interaction.followup.send("오류: 레이드 스레드를 찾을 수 없거나 올바른 타입이 아닙니다.", ephemeral=True)
                return

            original_message = await thread_channel.fetch_message(self.original_message_id)

            current_content = original_message.content
            new_character_name = self.character_name.value.strip() # 입력된 닉네임
            user_mention = interaction.user.mention # 신청한 사용자 멘션

            # '---' 구분자를 기준으로 참여 명단 이전 부분과 이후 부분을 나눕니다.
            participant_section_start = current_content.find("---\n**참여 명단")
            
            base_content = current_content # 초기에는 전체 내용
            current_participants_display = [] # 현재 참여 명단 (표시용)
            current_participants_count = 0
            max_participants = DEFAULT_MAX_PARTICIPANTS # 초기 최대 인원

            if participant_section_start != -1:
                # '---' 이전의 기본 내용
                base_content = current_content[:participant_section_start].strip()

                # '---' 이후의 참여 명단 부분
                participant_section_raw = current_content[participant_section_start:]

                # 현재 인원 수와 최대 인원 수 (X/Y) 파싱
                match_count = re.search(r"\((\d+)/(\d+)\)", participant_section_raw)
                if match_count:
                    current_participants_count = int(match_count.group(1))
                    max_participants = int(match_count.group(2))
                
                # 기존 참여자 목록 파싱 (캐릭터 닉네임과 멘션 포함된 형태 그대로 저장)
                for line in participant_section_raw.split('\n'):
                    line_stripped = line.strip()
                    if line_stripped.startswith('-'):
                        current_participants_display.append(line_stripped.lstrip('- ').strip())
            
            # 닉네임만 추출하여 중복 검사 (멘션 부분 제외)
            existing_char_names_for_check = [
                re.split(r'\s*\(', p_str)[0].strip() # 괄호 이전의 닉네임만 추출
                for p_str in current_participants_display
            ]

            # 중복 참여 확인
            if new_character_name in existing_char_names_for_check:
                await interaction.followup.send(f"'{new_character_name}'님은 이미 참여 명단에 있습니다.", ephemeral=True)
                return
            
            # 인원 초과 확인
            if current_participants_count >= max_participants:
                 await interaction.followup.send("⚠️ 레이드 인원이 모두 찼습니다.", ephemeral=True)
                 return

            # 새 참여자를 명단에 추가 (캐릭터 닉네임과 멘션 함께 저장)
            current_participants_display.append(f"{new_character_name} ({user_mention})")
            current_participants_count += 1

            # 참여 명단은 캐릭터 닉네임을 기준으로 알파벳순으로 정렬 (보기 좋게)
            # 정렬 시 멘션 부분은 제외하고 닉네임만 기준으로 합니다.
            current_participants_display.sort(key=lambda x: re.split(r'\s*\(', x)[0].strip())

            # 새로운 참여 명단 섹션을 재구성합니다.
            new_participant_section_lines = [
                f"---\n**참여 명단 ({current_participants_count}/{max_participants})**"
            ]
            for char_info_str in current_participants_display:
                new_participant_section_lines.append(f"- {char_info_str}")
            
            new_participant_section = "\n".join(new_participant_section_lines)

            # 원본 메시지 내용을 업데이트합니다.
            # 기존 레이드 정보와 새로 구성된 참여 명단 섹션을 합칩니다.
            new_content = f"{base_content}\n\n{new_participant_section}"
            
            await original_message.edit(content=new_content)
            await interaction.followup.send(f"'{new_character_name}'님의 참여 신청이 완료되었습니다! 명단을 확인해주세요.", ephemeral=True)

        except Exception as e:
            print(f"참여 신청 처리 중 오류 발생: {e}")
            await interaction.followup.send(f"참여 신청 중 오류가 발생했습니다: {e}", ephemeral=True)

# --- 참여 신청 버튼 뷰 정의 ---
class RaidSignupView(discord.ui.View):
    """
    레이드 모집 게시글에 포함될 '참여 신청' 버튼을 제공하는 뷰입니다.
    이 뷰는 봇 재시작 후에도 버튼이 활성화되도록 Persistent View로 설정됩니다.
    """
    def __init__(self):
        super().__init__(timeout=None) # 봇 재시작 후에도 버튼이 유지되도록 timeout=None 설정

    # '참여 신청' 버튼 정의
    # custom_id는 봇 재시작 후에도 이 버튼을 식별하기 위해 고유해야 합니다.
    @discord.ui.button(label="참여 신청", style=discord.ButtonStyle.success, custom_id="raid_signup_button")
    async def signup_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        # 버튼이 눌린 메시지(레이드 게시글)의 ID와 해당 메시지가 있는 스레드 ID를 가져옵니다.
        original_message_id = interaction.message.id
        thread_id = interaction.message.channel.id

        # 참여 신청 모달을 사용자에게 보여줍니다.
        await interaction.response.send_modal(RaidSignupModal(original_message_id, thread_id))

# --- 봇 이벤트 리스너 ---
@bot.event
async def on_ready():
    """
    봇이 디스코드에 성공적으로 연결되었을 때 실행됩니다.
    슬래시 명령어를 디스코드에 동기화하는 작업을 수행합니다.
    """
    print(f"[{bot.user}] 봇이 성공적으로 켜졌습니다.")
    # 현재 사용 중인 discord.py 버전을 출력하여 디버깅에 도움을 줍니다.
    print(f"discord.py version: {discord.__version__}")
    print("슬래시 명령어 '/레이드생성'과 헬스 체크, 참여 신청 기능이 활성화되었습니다.")
    print("슬래시 명령어를 디스코드에 동기화합니다...")
    try:
        # 슬래시 명령어를 디스코드에 등록(동기화)합니다.
        await bot.tree.sync() # 모든 서버에 동기화 (배포 시 권장)
        print("슬래시 명령어 동기화 완료.")
    except Exception as e:
        print(f"슬래시 명령어 동기화 실패: {e}")

# --- 봇 재시작 시 Persistent View 등록을 위한 setup_hook ---
@bot.event
async def setup_hook():
    """
    봇이 시작되기 전에 실행되는 훅입니다.
    봇 재시작 후에도 '참여 신청' 버튼이 정상 작동하도록 Persistent View를 등록합니다.
    """
    print("Persistent Views를 설정 중입니다...")
    # 'raid_signup_button' custom_id를 가진 모든 버튼에 대해
    # RaidSignupView 인스턴스가 처리하도록 등록합니다.
    bot.add_view(RaidSignupView())
    print("Persistent Views 설정 완료.")

# --- 슬래시 명령어 정의: '/레이드생성' ---
@bot.tree.command(name="레이드생성", description="로스트아크 레이드 모집 글을 포럼 채널에 올립니다.")
@app_commands.describe(
    월="레이드를 진행할 월 (예: 6)",
    일="레이드를 진행할 일 (예: 20)",
    시간="레이드를 진행할 시간 (24시간 형식, 예: 2130)",
    레이드종류="모집할 로스트아크 레이드 종류",
    숙련도="요구하는 숙련도",
    인원수="총 모집 인원 (기본값: 8, 1~16 사이)" # 인원수 파라미터 추가
)
@app_commands.choices(
    레이드종류=RAID_TYPE_CHOICES,
    숙련도=PROFICIENCY_CHOICES
)
async def create_raid(
    interaction: discord.Interaction,
    월: int,
    일: int,
    시간: int,
    레이드종류: app_commands.Choice[str],
    숙련도: app_commands.Choice[str],
    인원수: app_commands.Range[int, 1, 16] = DEFAULT_MAX_PARTICIPANTS # 선택 사항, 기본값 8, 범위 제한
):
    """로스트아크 레이드 모집 글을 포럼 채널에 올립니다."""

    current_year = datetime.now().year
    try:
        time_str = f"{시간 // 100:02d}:{시간 % 100:02d}"
        # 날짜 및 시간 유효성 검사 (유효하지 않은 날짜/시간은 ValueError 발생)
        datetime(current_year, 월, 일, 시간 // 100, 시간 % 100)
    except ValueError:
        # 오류 발생 시, defer 전에 응답을 보내야 하므로 interaction.response.send_message 사용
        await interaction.response.send_message(
            "날짜 또는 시간 형식이 올바르지 않습니다. 월, 일, 시간(HHMM 형식)을 확인해주세요.",
            ephemeral=True # 이 메시지는 명령어를 사용한 사람에게만 보입니다.
        )
        return

    # 설정된 포럼 채널 객체를 가져옵니다.
    forum_channel = bot.get_channel(FORUM_CHANNEL_ID)

    # 채널이 포럼 채널 타입이 아니거나 찾을 수 없는 경우 오류 처리
    if not isinstance(forum_channel, discord.ForumChannel):
        # 오류 발생 시, defer 전에 응답을 보내야 하므로 interaction.response.send_message 사용
        await interaction.response.send_message(
            f"설정된 채널 ID({FORUM_CHANNEL_ID})를 찾을 수 없거나 포럼 채널이 아닙니다. 관리자에게 문의하세요.",
            ephemeral=True
        )
        print(f"오류: 설정된 채널 ID({FORUM_CHANNEL_ID})가 포럼 채널이 아니거나 찾을 수 없습니다.")
        return

    raid_type_display = 레이드종류.name # 사용자에게 보이는 레이드 종류 이름
    proficiency_display = 숙련도.name # 사용자에게 보이는 숙련도 이름

    # 포럼 게시글의 제목을 구성합니다.
    post_title = f"[{raid_type_display}] {월}월 {일}일 {time_str} 레이드 모집 ({proficiency_display})"
    
    # 포럼 게시글의 초기 내용을 구성합니다.
    post_content = (
        f"**__레이드 모집 정보__**\n"
        f"**날짜:** {월}월 {일}일\n"
        f"**시간:** {time_str}\n"
        f"**레이드 종류:** {raid_type_display}\n"
        f"**숙련도:** {proficiency_display}\n\n"
        f"✅ 참여를 원하시는 분은 아래 '참여 신청' 버튼을 눌러주세요!\n"
        f"작성자: {interaction.user.mention}\n\n" # 명령어를 실행한 사용자 멘션
        f"---\n" # 참여 명단과 레이드 정보 구분을 위한 구분선
        f"**참여 명단 (0/{인원수})**\n" # 초기 참여 명단 (현재 0명)
    )

    try:
        # 명령어를 받았음을 디스코드에 즉시 알려주는 응답
        # 이제 defer는 오류 발생 여부와 상관없이 무조건 첫 응답으로 보냅니다.
        await interaction.response.defer(ephemeral=False) 

        # 포럼 스레드를 생성하며, 첫 메시지의 내용과 뷰를 함께 전달합니다.
        new_thread = await forum_channel.create_thread(
            name=post_title,
            content=post_content, # 첫 메시지 내용
            view=RaidSignupView(), # 첫 메시지에 첨부할 뷰
            auto_archive_duration=1440 # 24시간 후 자동 아카이브 (분 단위)
        )
        
        # 게시글이 생성된 후, 생성된 스레드(new_thread)의 jump_url을 직접 사용합니다.
        jump_url = new_thread.jump_url 

        # defer 응답을 따라가는 followup.send 사용 (성공 메시지)
        await interaction.followup.send(
            f"레이드 모집 글이 포럼 채널에 성공적으로 생성되었습니다: {jump_url}",
            ephemeral=False # 이 메시지는 모든 사람이 볼 수 있도록 공개합니다.
        )

    except discord.Forbidden:
        # 봇에게 포럼 채널에 게시글을 작성할 권한이 없을 경우
        # 이미 defer 응답을 보냈으므로, followup.send 사용
        await interaction.followup.send(
            "봇이 포럼 채널에 게시글을 작성할 권한이 없습니다. 봇 권한을 확인해주세요.",
            ephemeral=True
        )
        print(f"오류: 봇이 채널 {FORUM_CHANNEL_ID}에 게시글을 작성할 권한이 없습니다.")
    except Exception as e:
        # 그 외 예상치 못한 오류 발생 시, 오류 메시지를 더 자세히 출력합니다.
        # 이미 defer 응답을 보냈으므로, followup.send 사용
        await interaction.followup.send(
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


import json
import re
from bs4 import BeautifulSoup
import pymysql
import time
from playwright.sync_api import sync_playwright

# ==========================================
# 1. MySQL DB 연결 설정
# ==========================================
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "root0312@",  # 본인의 DB 비밀번호로 수정하세요
    "database": "banhub_db",
    "charset": "utf8mb4",
    "autocommit": True,
}


def get_db_connection():
    return pymysql.connect(**DB_CONFIG, cursorclass=pymysql.cursors.DictCursor)


# ==========================================
# 2. HTML 카드 정밀 파싱 및 DB 저장 함수
# ==========================================
def parse_and_save_dom(html):
    soup = BeautifulSoup(html, "html.parser")

    # 실제 벤허브 DOM 구조에 맞는 개별 제재 카드 박스 타겟팅
    cards = soup.select(
        "div[class*='flex'][class*='flex-col'][class*='bg-neutral-950']"
    )
    if not cards:
        cards = soup.select("a[href*='/soop/user/']")

    print(f"\n🔍 화면에서 총 {len(cards)}개의 제재 카드 박스 발견!")

    conn = get_db_connection()
    total_saved = 0

    try:
        with conn.cursor() as cursor:
            for card_idx, card in enumerate(cards):
                # 0) 유저 ID 추출
                user_link = card.select_one("a[href*='/soop/user/']")
                user_id = (
                    user_link.get("href").split("/")[-1]
                    if user_link
                    else f"unknown_{card_idx}"
                )

                lines = [
                    t.strip()
                    for t in card.get_text(separator="\n").split("\n")
                    if t.strip()
                ]
                card_full_text = " ".join(lines)

                # --------------------------------------------------
                # 1) 우상단 제재 일시 정밀 추출
                # --------------------------------------------------
                sanction_time = None

                for line in lines:
                    time_match = re.search(
                        r"(\d{2})\.(\d{2})\.(\d{2})\s+(\d{2}:\d{2}:\d{2})", line
                    )
                    if time_match:
                        yy, mm, dd, hhmmss = time_match.groups()
                        sanction_time = f"20{yy}-{mm}-{dd} {hhmmss}"
                        break

                if not sanction_time:
                    date_elem = card.find(
                        string=re.compile(r"^\d{2}\.\d{2}\.\d{2}$")
                    )
                    time_elem = card.find(
                        string=re.compile(r"^\d{2}:\d{2}:\d{2}$")
                    )

                    if date_elem and time_elem:
                        d_match = re.search(
                            r"(\d{2})\.(\d{2})\.(\d{2})", date_elem.strip()
                        )
                        t_match = re.search(r"(\d{2}:\d{2}:\d{2})", time_elem.strip())
                        if d_match and t_match:
                            yy, mm, dd = d_match.groups()
                            hhmmss = t_match.group(1)
                            sanction_time = f"20{yy}-{mm}-{dd} {hhmmss}"

                if not sanction_time:
                    sanction_time = time.strftime("%Y-%m-%d %H:%M:%S")

                # --------------------------------------------------
                # 2) 처리 매니저 닉네임 정밀 추출
                # --------------------------------------------------
                manager_nick = "BJ/매니저"
                if "처리자" in lines:
                    p_idx = lines.index("처리자")
                    if p_idx + 1 < len(lines):
                        cand = lines[p_idx + 1]
                        if not re.match(r"^\d+$", cand) and cand not in [
                            "이상호",
                            "처리자",
                        ]:
                            manager_nick = cand

                # --------------------------------------------------
                # 3) 제재 유형 판별 (채금 / 강퇴 / 블랙)
                # --------------------------------------------------
                action_type = "KICK"
                if "강퇴" in card_full_text:
                    action_type = "KICK"
                elif "채금" in card_full_text or "임차" in card_full_text:
                    action_type = "MUTE"
                elif "블랙" in card_full_text or "BAN" in card_full_text:
                    action_type = "BAN"

                # --------------------------------------------------
                # 4) 유저 닉네임 정밀 추출 (채금/강퇴 구조 차이 완벽 반영)
                # --------------------------------------------------
                ignore_list = [
                    "이상호",
                    "처리자",
                    manager_nick,
                    "팬",
                    "열혈",
                    "서포터",
                    "매니저",
                    "강퇴",
                    "채금",
                    "블랙",
                ]
                
                user_nick = user_id
                user_link_elem = card.select_one("a[href*='/soop/user/']")
                
                if user_link_elem:
                    spans = user_link_elem.find_all("span")
                    for span in spans:
                        span_class = span.get("class", [])
                        parent_class = span.parent.get("class", []) if span.parent else []
                        
                        if "mr-3" in span_class or "mr-3" in parent_class:
                            continue
                        
                        txt = span.get_text(strip=True)
                        if not txt:
                            continue
                        
                        if any(bad in txt for bad in ["채금", "강퇴", "블랙", "30초", "초)", "분)"]):
                            continue
                        
                        user_nick = txt
                        break

                if user_nick == user_id or any(bad in user_nick for bad in ["채금", "30초"]):
                    for line in lines:
                        if (
                            re.search(r"^\d{2}\.\d{2}\.\d{2}", line)
                            or re.match(r"^\d{2}:\d{2}:\d{2}$", line)
                            or line in ignore_list
                            or re.search(r"^\(.*\)$", line)
                            or re.search(r"^(채금|강퇴|블랙)", line)
                            or line == manager_nick
                        ):
                            continue
                        user_nick = line
                        break

                # --------------------------------------------------
                # 5) 채팅 기록 수집 ('포럼 및 채팅 제공자' 필터링 포함)
                # --------------------------------------------------
                chat_lines = []
                i = 0
                while i < len(lines):
                    line = lines[i]
                    if re.match(r"^\d{2}:\d{2}:\d{2}$", line):
                        if (
                            sanction_time
                            and line in sanction_time
                            and i < 3
                        ):
                            i += 1
                            continue

                        if i + 1 < len(lines):
                            msg = lines[i + 1]
                            
                            # '포럼 및 채팅 제공자' 시스템 문구는 수집 대상에서 제외
                            if "포럼 및 채팅 제공자" in msg:
                                i += 2
                                continue

                            if (
                                msg not in ignore_list
                                and msg != "처리자"
                                and msg != manager_nick
                                and not re.match(r"^\d+$", msg)
                                and not re.match(r"^\d{2}\.\d{2}\.\d{2}$", msg)
                            ):
                                chat_lines.append(f"[{line}] {msg}")
                                i += 1
                    i += 1

                chat_context_json = json.dumps(chat_lines, ensure_ascii=False)

                # 고유 키 생성 (중복 방지)
                unique_key = f"{user_id}_{action_type}_{sanction_time}_{card_idx}"

                # DB 중복 체크
                cursor.execute(
                    "SELECT id FROM sanction_logs WHERE unique_sanction_key = %s",
                    (unique_key,),
                )
                if cursor.fetchone():
                    continue

                # 1) sanctioned_users 테이블 저장/업데이트
                sql_user = """
                INSERT INTO sanctioned_users 
                    (user_id, user_nickname, total_kicks, total_mutes, total_bans, first_sanction_at, last_sanction_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON DUPLICATE KEY UPDATE
                    user_nickname = VALUES(user_nickname),
                    total_kicks = total_kicks + IF(VALUES(total_kicks)>0, 1, 0),
                    total_mutes = total_mutes + IF(VALUES(total_mutes)>0, 1, 0),
                    total_bans = total_bans + IF(VALUES(total_bans)>0, 1, 0),
                    last_sanction_at = VALUES(last_sanction_at);
                """
                kick_val = 1 if action_type == "KICK" else 0
                mute_val = 1 if action_type == "MUTE" else 0
                ban_val = 1 if action_type == "BAN" else 0

                cursor.execute(
                    sql_user,
                    (
                        user_id,
                        user_nick,
                        kick_val,
                        mute_val,
                        ban_val,
                        sanction_time,
                        sanction_time,
                    ),
                )

                # 2) sanction_logs 테이블 저장
                sql_log = """
                INSERT INTO sanction_logs 
                    (unique_sanction_key, user_id, user_nickname, action_type, manager_nickname, chat_context, sanction_time)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(
                    sql_log,
                    (
                        unique_key,
                        user_id,
                        user_nick,
                        action_type,
                        manager_nick,
                        chat_context_json,
                        sanction_time,
                    ),
                )
                total_saved += 1

        if total_saved > 0:
            print(f"💾 이번 주기 신규 {total_saved}건 DB 동기화 완료!")
        else:
            print("✨ 최신 동기화 대상 신규 내역이 없습니다.")

    finally:
        conn.close()


# ==========================================
# 3. 스케줄러가 호출하는 주기적 실행 함수
# ==========================================
def run_periodic_collector():
    target_url = "https://banhub.xyz/soop/streamer/lshooooo"
    print(f"\n[스케줄러 작업 시작] 🌐 {target_url} 접속 및 최신 제재 내역 동기화 중...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        try:
            page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
            page.wait_for_timeout(3000)

            html_content = page.content()
            parse_and_save_dom(html_content)

        except Exception as e:
            print(f"❌ 주기적 수집 중 오류 발생: {e}")
        finally:
            browser.close()
            print("[스케줄러 작업 완료]")


if __name__ == "__main__":
    run_periodic_collector()
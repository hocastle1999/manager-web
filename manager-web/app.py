from flask import Flask, render_template, request, redirect, url_for, session
import pymysql
from pyngrok import ngrok  # pyngrok 라이브러리 추가

app = Flask(__name__)
app.secret_key = "your_secret_key_here"  # 세션 암호화를 위한 임의의 비밀키

# MySQL DB 연결 설정
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "root0312@",  # 본인의 DB 비밀번호로 수정
    "database": "banhub_db",
    "charset": "utf8mb4",
    "cursorclass": pymysql.cursors.DictCursor,
    "autocommit": True
}

# [설정] 허락된 관리자 계정 정보 (아이디와 비밀번호) -> 이 부분을 수정하세요!
ALLOWED_USERS = {
    "원하는아이디": "원하는비밀번호"  # 관리자 계정
}


def get_db():
    return pymysql.connect(**DB_CONFIG)


# 로그인 페이지
@app.route("/", methods=["GET", "POST"])
def login():
    error = None
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        if username in ALLOWED_USERS and ALLOWED_USERS[username] == password:
            session["logged_in"] = True
            session["user"] = username
            return redirect(url_for("dashboard"))
        else:
            error = "아이디 또는 비밀번호가 올바르지 않습니다."

    return render_template("login.html", error=error)


# 대시보드 (실시간 모니터링 - 매니저 필터 및 블랙 제외)
@app.route("/dashboard")
def dashboard():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    # 사용자가 선택한 매니저 이름 (선택 안 했으면 전체)
    selected_manager = request.args.get("manager", "")

    conn = get_db()
    try:
        with conn.cursor() as cursor:
            # 1. 드롭다운 필터용 매니저 목록 조회
            cursor.execute(
                "SELECT DISTINCT manager_nickname FROM sanction_logs WHERE manager_nickname IS NOT NULL AND manager_nickname != ''")
            managers = cursor.fetchall()

            # 2. 제재 내역 조회 쿼리 (매니저 선택 여부에 따라 분기)
            if selected_manager:
                query = """
                    SELECT 
                        MIN(id) as id,
                        sanction_time, 
                        user_id, 
                        MAX(user_nickname) as user_nickname, 
                        action_type, 
                        MAX(manager_nickname) as manager_nickname, 
                        chat_context
                    FROM sanction_logs 
                    WHERE action_type IN ('MUTE', 'KICK') AND manager_nickname = %s
                    GROUP BY sanction_time, user_id, action_type, chat_context
                    ORDER BY sanction_time DESC
                """
                cursor.execute(query, (selected_manager,))
            else:
                query = """
                    SELECT 
                        MIN(id) as id,
                        sanction_time, 
                        user_id, 
                        MAX(user_nickname) as user_nickname, 
                        action_type, 
                        MAX(manager_nickname) as manager_nickname, 
                        chat_context
                    FROM sanction_logs 
                    WHERE action_type IN ('MUTE', 'KICK')
                    GROUP BY sanction_time, user_id, action_type, chat_context
                    ORDER BY sanction_time DESC
                """
                cursor.execute(query)

            logs = cursor.fetchall()

            # 3. 총 제재 통계 요약 (필터 적용 상태 연동)
            if selected_manager:
                count_query = """
                    SELECT COUNT(DISTINCT sanction_time, user_id, action_type, chat_context) as total_count 
                    FROM sanction_logs
                    WHERE action_type IN ('MUTE', 'KICK') AND manager_nickname = %s
                """
                cursor.execute(count_query, (selected_manager,))
            else:
                count_query = """
                    SELECT COUNT(DISTINCT sanction_time, user_id, action_type, chat_context) as total_count 
                    FROM sanction_logs
                    WHERE action_type IN ('MUTE', 'KICK')
                """
                cursor.execute(count_query)

            total_stats = cursor.fetchone()
    finally:
        conn.close()

    return render_template("dashboard.html", logs=logs, total_stats=total_stats, managers=managers,
                           selected_manager=selected_manager)


# 유저별 제재 횟수 통계 페이지
@app.route("/ranking")
def ranking():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    conn = get_db()
    try:
        with conn.cursor() as cursor:
            query = """
                SELECT 
                    user_nickname, 
                    user_id, 
                    COUNT(*) as sanction_count,
                    SUM(CASE WHEN action_type = 'MUTE' THEN 1 ELSE 0 END) as mute_count,
                    SUM(CASE WHEN action_type = 'KICK' THEN 1 ELSE 0 END) as kick_count
                FROM sanction_logs 
                WHERE action_type IN ('MUTE', 'KICK')
                GROUP BY user_id, user_nickname
                ORDER BY sanction_count DESC
            """
            cursor.execute(query)
            user_rankings = cursor.fetchall()
    finally:
        conn.close()

    return render_template("ranking.html", rankings=user_rankings)


# 로그아웃
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


if __name__ == "__main__":
    ngrok.kill()
    public_url = ngrok.connect(5000, domain="uncivil-bunion-eatable.ngrok-free.dev")
    print(f"\n * 고정 외부 공유 링크(Ngrok URL): {public_url}\n")
    app.run(debug=True, port=5000, use_reloader=False)
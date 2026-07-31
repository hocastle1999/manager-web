# 🌐 Manager Web & Collector

Playwright 크롤러와 Flask, MySQL을 활용한 실시간 제재 내역 수집 및 관리 웹 대시보드 시스템입니다.

## 🛠️ Tech Stack
* **Language**: Python 3.10+
* **Web Framework**: Flask
* **Database**: MySQL (PyMySQL)
* **Automation & Scraping**: Playwright, BeautifulSoup4
* **Scheduler**: APScheduler
* **Deployment/Tunneling**: Ngrok

## ✨ Key Features
* **Playwright 자동화 크롤러 (`chat_manager.py`)**
  * 웹페이지의 제재 카드 DOM 파싱 및 날짜/시간, 매니저, 채팅 기록 정밀 추출
  * '내역 더 불러오기' 버튼 무한 클릭 및 스크롤을 통한 과거 제재 내역 전수 수집
  * MySQL 데이터베이스 중복 방지 저장 (`ON DUPLICATE KEY UPDATE`) 및 통계 자동 업데이트
* **주기적 백그라운드 동기화 (`scheduler.py`)**
  * **APScheduler**를 적용하여 일정 시간(5분)마다 백그라운드에서 최신 제재 내역 자동 수집
  * 웹 서버 동작과 분리되어 안정적인 주기적 DB 데이터 최신화 지원
* **Flask 관리자 대시보드 (`app.py`)**
  * 매니저별/유저별 필터링 기능이 포함된 실시간 제재 내역 모니터링
  * 유저별 제재 횟수(채금, 강퇴, 블랙) 순위 통계 및 상세 채팅 맥락(Chat Context) 조회
  * Ngrok 고정 도메인을 활용한 외부 접속 공유 및 테스트 지원

## 📁 Project Structure
```text
my_web_app/
├── app.py              # Flask 웹 대시보드 서버 실행 파일
├── chat_manager.py     # DOM 파싱 및 DB 저장/수집 핵심 로직 모듈
├── scheduler.py        # 5분 주기 자동 수집 스케줄러 실행 파일
├── templates/          # 웹 대시보드 HTML 템플릿
└── static/             # CSS/JS 정적 파일

# 🌐 Manager Web & Collector

Playwright 크롤러와 Flask, MySQL을 활용한 실시간 제재 내역 수집 및 관리 웹 대시보드 시스템입니다.

## 🛠️ Tech Stack
* Python
* Flask
* PyMySQL
* Playwright
* BeautifulSoup4
* Ngrok

## ✨ Features
* **Playwright 자동화 크롤러 (`collector.py`)**: 
  * 웹페이지의 제재 카드 DOM 파싱 및 날짜/시간, 매니저, 채팅 기록 정밀 추출
  * '내역 더 불러오기' 버튼 무한 클릭 및 스크롤을 통한 과거 제재 내역 전수 수집
  * MySQL 데이터베이스 중복 방지 저장 및 통계 자동 업데이트
* **Flask 관리자 대시보드 (`app.py`)**:
  * 매니저별 필터링 기능이 포함된 실시간 제재 내역 모니터링
  * 유저별 제재 횟수(채금, 강퇴 등) 순위 통계 페이지 제공
  * Ngrok을 활용한 외부 공유 및 로컬 테스트 환경 지원

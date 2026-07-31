# scheduler.py
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.interval import IntervalTrigger

# chat_manager.py의 주기적 수집 함수 호출
from chat_manager import run_periodic_collector

if __name__ == "__main__":
    scheduler = BlockingScheduler(timezone="Asia/Seoul")

    # 5분(minutes=5) 주기로 자동 실행 설정
    scheduler.add_job(
        run_periodic_collector,
        trigger=IntervalTrigger(minutes=5),
        id="banhub_crawler_job",
        name="밴허브 최신 제재 내역 동기화",
        replace_existing=True,
    )

    print("===========================================")
    print("⏰ APScheduler가 시작되었습니다. (5분 주기)")
    print("   종료하려면 Ctrl + C 를 누르세요.")
    print("===========================================")

    # 스케줄러를 가동하자마자 최초 1회 즉시 실행
    run_periodic_collector()

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("\n🛑 스케줄러가 정상적으로 종료되었습니다.")
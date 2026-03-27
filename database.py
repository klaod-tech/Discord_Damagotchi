# database.py — utils/db.py의 init_db를 직접 실행하는 진입점 (하위 호환용)
from utils.db import init_db

if __name__ == "__main__":
    init_db()
    print("DB 초기화 완료")

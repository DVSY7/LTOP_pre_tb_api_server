import os
import mariadb

from dotenv import load_dotenv
from fastapi import FastAPI, Form, HTTPException


# 로컬 실행 시 .env 파일 로드
load_dotenv()

app = FastAPI(
    title="PRE TB API",
    version="0.5.0"
)


# =========================================================
# DB 연결
# =========================================================
def get_db_connection():
    return mariadb.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", "43306")),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_NAME")
    )


# =========================================================
# DB INSERT
# =========================================================
def insert_tb_data(
    equip_id: str,
    bettery: float,
    inner_temp: float,
    corrol_volt: float,
    inner_humidity: float
):
    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        sql = """
            INSERT INTO stat_pre_tb (
                equip_id,
                bettery,
                inner_temp,
                corrol_volt,
                inner_humidity
            )
            VALUES (?, ?, ?, ?, ?)
        """

        cursor.execute(
            sql,
            (
                equip_id,
                bettery,
                inner_temp,
                corrol_volt,
                inner_humidity
            )
        )

        conn.commit()

        return cursor.lastrowid

    except mariadb.Error:
        if conn:
            conn.rollback()
        raise

    finally:
        if cursor:
            cursor.close()

        if conn:
            conn.close()


# =========================================================
# Health Check
# =========================================================
@app.get("/health")
def health():
    return {
        "status": "OK"
    }


# =========================================================
# TB 데이터 수신
# =========================================================
@app.post("/api/v1/tb/data")
def receive_tb_data(
    e: str = Form(...),
    b: float = Form(...),
    t: float = Form(...),
    cv: float = Form(...),
    h: float = Form(...)
):
    # 짧은 통신 Key → 실제 DB 변수명
    tb_data = {
        "equip_id": e,
        "bettery": b,
        "inner_temp": t,
        "corrol_volt": cv,
        "inner_humidity": h
    }

    print("\n[TB DATA RECEIVED]")

    for key, value in tb_data.items():
        print(f"{key:15} = {value}")

    try:
        t_no = insert_tb_data(
            equip_id=e,
            bettery=b,
            inner_temp=t,
            corrol_volt=cv,
            inner_humidity=h
        )

        print(f"[DB INSERT SUCCESS] t_no={t_no}")

        # DB 저장까지 성공한 경우에만 OK 반환
        return {
            "result": "OK",
            "equip_id": e,
            "t_no": t_no
        }

    except mariadb.Error as error:
        print(f"[DB INSERT ERROR] {error}")

        raise HTTPException(
            status_code=500,
            detail="DB INSERT FAILED"
        )
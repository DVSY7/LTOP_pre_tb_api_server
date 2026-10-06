from fastapi import FastAPI, Form, HTTPException

app = FastAPI(
    title="PRE TB API",
    version="0.3.0"
)


@app.get("/health")
def health():
    return {
        "status": "OK"
    }


@app.post("/api/v1/tb/data")
def receive_tb_data(
    v: int = Form(...),
    s: int = Form(...),
    e: str = Form(...),
    b: float = Form(...),
    t: float = Form(...),
    cv: float = Form(...),
    os: int = Form(...),
    om: int = Form(...),
    ec: int = Form(...),
    a: int | None = Form(None),
    br: int | None = Form(None),
    h: float | None = Form(None),
    max: float = Form(-850),
    min: float = Form(-2500)
):

    # --------------------------------------------------------
    # Protocol Version 확인
    # --------------------------------------------------------

    if v != 1:
        raise HTTPException(
            status_code=400,
            detail="Unsupported protocol version"
        )

    # --------------------------------------------------------
    # 통신용 필드 → DB 컬럼명 매핑
    # --------------------------------------------------------

    tb_data = {
        "site_id": s,
        "equip_id": e,
        "bettery": b,
        "inner_temp": t,
        "corrol_volt": cv,
        "op_status_id": os,
        "op_mode_id": om,
        "error_code_id": ec,
        "area_id": a,
        "branch_id": br,
        "inner_humidity": h,
        "max_set_volt": max,
        "min_set_volt": min
    }

    # --------------------------------------------------------
    # 현재는 DB 저장 전이므로 로그만 출력
    # --------------------------------------------------------

    print("\n[TB DATA RECEIVED]")
    print(f"protocol_version = {v}")

    for key, value in tb_data.items():
        print(f"{key:15} = {value}")

    # --------------------------------------------------------
    # 추후 여기에서 DB INSERT
    # --------------------------------------------------------

    # insert_stat_tb(tb_data)

    # --------------------------------------------------------
    # ACK
    # --------------------------------------------------------

    return {
        "result": "OK",
        "equip_id": e
    }
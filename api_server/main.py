from fastapi import FastAPI, Form

app = FastAPI(
    title="PRE TB API",
    version="0.4.0"
)


@app.get("/health")
def health():
    return {
        "status": "OK"
    }


@app.post("/api/v1/tb/data")
def receive_tb_data(
    e: str = Form(...),
    b: float = Form(...),
    t: float = Form(...),
    cv: float = Form(...),
    h: float = Form(...)
):
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

    # 추후 DB INSERT
    # insert_stat_tb(tb_data)

    return {
        "result": "OK",
        "equip_id": e
    }
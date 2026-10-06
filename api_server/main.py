from fastapi import FastAPI, Form

app = FastAPI(
    title="PRE TB API",
    version="0.2.0"
)


@app.get("/health")
def health():
    return {"status": "OK"}


@app.post("/api/v1/tb/data")
def receive_tb_data(
    site_id: int = Form(...),
    equip_id: str = Form(...),
    bettery: float = Form(...),
    inner_temp: float = Form(...),
    corrol_volt: float = Form(...),
    op_status_id: int = Form(...),
    op_mode_id: int = Form(...),
    error_code_id: int = Form(...),
    area_id: int | None = Form(None),
    branch_id: int | None = Form(None),
    inner_humidity: float | None = Form(None),
    max_set_volt: float = Form(-850),
    min_set_volt: float = Form(-2500)
):
    print("\n[TB DATA RECEIVED]")

    print(f"site_id        = {site_id}")
    print(f"equip_id       = {equip_id}")
    print(f"bettery        = {bettery}")
    print(f"inner_temp     = {inner_temp}")
    print(f"corrol_volt    = {corrol_volt}")
    print(f"op_status_id   = {op_status_id}")
    print(f"op_mode_id     = {op_mode_id}")
    print(f"error_code_id  = {error_code_id}")
    print(f"area_id        = {area_id}")
    print(f"branch_id      = {branch_id}")
    print(f"inner_humidity = {inner_humidity}")
    print(f"max_set_volt   = {max_set_volt}")
    print(f"min_set_volt   = {min_set_volt}")

    return {
        "result": "OK",
        "equip_id": equip_id
    }

@app.post("/api/v1/tb/test-data")
def receive_tb_test_data(
    site_id: int = Form(...),
    equip_id: str = Form(...),
    bettery: float = Form(...),
    inner_temp: float = Form(...),
    corrol_volt: float = Form(...)
):
    print(
        f"[TB TEST RECV] "
        f"site_id={site_id}, "
        f"equip_id={equip_id}, "
        f"bettery={bettery}, "
        f"inner_temp={inner_temp}, "
        f"corrol_volt={corrol_volt}"
    )

    return {
        "result": "OK",
        "equip_id": equip_id
    }
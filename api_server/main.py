from fastapi import FastAPI, Form
from pydantic import BaseModel


app = FastAPI(
    title="PRE TB API",
    version="0.1.0"
)


# TB에서 받을 테스트 데이터 형식
class TBData(BaseModel):
    sequence: int
    message: str


# 서버가 살아있는지 확인
@app.get("/health")
def health():
    return {
        "status": "OK"
    }


# TB 데이터 수신 - JSON
@app.post("/api/v1/tb/data")
def receive_tb_data(data: TBData):

    print(
        f"[RECV] sequence={data.sequence}, "
        f"message={data.message}"
    )

    return {
        "result": "OK",
        "sequence": data.sequence
    }


# LTE 모뎀 통신 테스트용 - Form
@app.post("/api/v1/tb/test")
def receive_tb_test(
    sequence: int = Form(...),
    message: str = Form(...)
):
    print(
        f"[LTE RECV] sequence={sequence}, "
        f"message={message}"
    )

    return {
        "result": "OK",
        "sequence": sequence
    }
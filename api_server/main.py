from fastapi import FastAPI
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


# TB 데이터 수신
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
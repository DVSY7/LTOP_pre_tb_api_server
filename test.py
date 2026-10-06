import serial
import time

PORT = "COM8"
BAUDRATE = 115200


def send_at(ser, command, wait=1):
    ser.reset_input_buffer()

    print(f"\n[SEND] {command}")

    ser.write((command + "\r\n").encode())
    ser.flush()

    time.sleep(wait)

    response = ser.read_all().decode(
        "utf-8",
        errors="replace"
    )

    print("[RECV]")
    print(response.strip())

    return response


ser = serial.Serial(
    port=PORT,
    baudrate=BAUDRATE,
    timeout=2
)

time.sleep(1)

# 기본 통신 확인
send_at(ser, "AT")

# LTE 데이터 연결 확인
send_at(ser, "AT+CGATT?")
send_at(ser, "AT+CGACT?")
send_at(ser, "AT+CGPADDR=1")

# HTTP GET 설정
send_at(
    ser,
    "AT*WHTTP=0,GET,httpbin.org/get,80",
    wait=2
)

# 설정 확인
send_at(
    ser,
    "AT*WHTTP?",
    wait=1
)

# HTTP 요청 실행
send_at(
    ser,
    "AT*WHTTP=3",
    wait=10
)

ser.close()
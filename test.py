import serial
import time


# ==============================
# Serial 설정
# ==============================
PORT = "COM8"
BAUDRATE = 115200

# Render API
HOST = "ltop-pre-tb-api-server.onrender.com"
PATH = "/api/v1/tb/data"
HTTPS_PORT = 443


# ==============================
# AT 명령 전송
# ==============================
def send_at(ser, command, wait=1):
    print(f"\n>> {command}")

    ser.write((command + "\r\n").encode())
    time.sleep(wait)

    response = ser.read_all().decode(errors="ignore")

    print(response)

    return response


# ==============================
# Main
# ==============================
def main():

    ser = serial.Serial(
        port=PORT,
        baudrate=BAUDRATE,
        timeout=2
    )

    try:
        # --------------------------
        # 테스트 TB 데이터
        # --------------------------
        equip_id = "TB001"
        bettery = 3.7
        inner_temp = 25.4
        corrol_volt = -920.5
        inner_humidity = 55.2

        # --------------------------
        # Payload 생성
        # --------------------------
        payload = (
            f"e={equip_id}"
            f"&b={bettery}"
            f"&t={inner_temp}"
            f"&cv={corrol_volt}"
            f"&h={inner_humidity}"
        )

        print("\n[PAYLOAD]")
        print(payload)

        # --------------------------
        # HTTP POST 설정
        # --------------------------
        command = (
            f"AT*WHTTP=1,POST,"
            f"{HOST}{PATH},"
            f"{HTTPS_PORT},,,"
            f"'{payload}'"
        )

        response = send_at(
            ser,
            command,
            wait=1
        )

        # --------------------------
        # HTTP 실행
        # --------------------------
        response = send_at(
            ser,
            "AT*WHTTP=3",
            wait=5
        )

        print("\n[TEST COMPLETE]")

    finally:
        ser.close()


if __name__ == "__main__":
    main()
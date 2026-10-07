import serial
import time


# ============================================================
# 설정
# ============================================================

PORT = "COM8"
BAUDRATE = 115200

RESPONSE_TIMEOUT = 15

HOST = "ltop-pre-tb-api-server.onrender.com"
PATH = "/api/v1/tb/data"
HTTPS_PORT = 443


# ============================================================
# AT 명령 전송
# ============================================================

def send_command(ser, command, timeout=2):

    ser.reset_input_buffer()

    print(f"\n[SEND] {command}")

    ser.write(
        (command + "\r\n").encode()
    )
    ser.flush()

    end_time = time.time() + timeout
    response = ""

    while time.time() < end_time:

        if ser.in_waiting:

            data = ser.read(
                ser.in_waiting
            ).decode(
                "utf-8",
                errors="replace"
            )

            response += data

        if (
            "\nOK" in response
            or "\nERROR" in response
        ):
            break

        time.sleep(0.01)

    print("[RECV]")
    print(response.strip())

    return response


# ============================================================
# HTTP 실행
# ============================================================

def execute_http(ser, timeout=15):

    ser.reset_input_buffer()

    print("\n[SEND] AT*WHTTP=3")

    start_time = time.perf_counter()

    ser.write(b"AT*WHTTP=3\r\n")
    ser.flush()

    response = ""
    deadline = time.time() + timeout

    while time.time() < deadline:

        if ser.in_waiting:

            data = ser.read(
                ser.in_waiting
            ).decode(
                "utf-8",
                errors="replace"
            )

            response += data

            if "*WHTTPR:COMPLETED" in response:

                rtt = time.perf_counter() - start_time

                print("[RECV]")
                print(response.strip())

                return True, response, rtt

            if "*WHTTPR:EXEC_FAILED" in response:

                rtt = time.perf_counter() - start_time

                print("[RECV]")
                print(response.strip())

                return False, response, rtt

        time.sleep(0.01)

    rtt = time.perf_counter() - start_time

    print("[TIMEOUT]")
    print(response.strip())

    return False, response, rtt


# ============================================================
# ACK 확인
# ============================================================

def check_ack(response, equip_id):

    return (
        '"result":"OK"' in response
        and f'"equip_id":"{equip_id}"' in response
    )


# ============================================================
# Main
# ============================================================

def main():

    print("=" * 60)
    print("PRE TB LTE -> API 전송 시험")
    print("=" * 60)

    # --------------------------------------------------------
    # TB 테스트 데이터
    # --------------------------------------------------------

    equip_id = "TB001"
    bettery = 3.7
    inner_temp = 25.4
    corrol_volt = -920.5
    inner_humidity = 55.2

    # --------------------------------------------------------
    # Payload 생성
    # --------------------------------------------------------

    payload = (
        f"e={equip_id}"
        f"&b={bettery}"
        f"&t={inner_temp}"
        f"&cv={corrol_volt}"
        f"&h={inner_humidity}"
    )

    payload_bytes = len(payload.encode("utf-8"))

    # WD-L700K에서 & 문자를 포함한 DATA 전체를 작은따옴표로 감싼다.
    data = f"'{payload}'"

    print("\n[TB DATA]")
    print(f"equip_id       : {equip_id}")
    print(f"bettery        : {bettery}")
    print(f"inner_temp     : {inner_temp}")
    print(f"corrol_volt    : {corrol_volt}")
    print(f"inner_humidity : {inner_humidity}")

    print("\n[PAYLOAD]")
    print(payload)

    print(f"\nPayload length : {payload_bytes} bytes")

    # --------------------------------------------------------
    # Serial 연결
    # --------------------------------------------------------

    with serial.Serial(
        port=PORT,
        baudrate=BAUDRATE,
        timeout=0.1
    ) as ser:

        time.sleep(1)

        # ----------------------------------------------------
        # 모뎀 / LTE 상태 확인
        # ----------------------------------------------------

        send_command(
            ser,
            "AT"
        )

        send_command(
            ser,
            "AT+CGATT?"
        )

        send_command(
            ser,
            "AT+CGACT?"
        )

        send_command(
            ser,
            "AT+CGPADDR=1"
        )

        print("\n" + "=" * 60)
        print("TB 데이터 전송")
        print("=" * 60)

        # ----------------------------------------------------
        # WHTTP 설정
        # ----------------------------------------------------

        command = (
            "AT*WHTTP=1,"
            "POST,"
            f"{HOST}{PATH},"
            f"{HTTPS_PORT},,,"
            f"{data}"
        )

        config_response = send_command(
            ser,
            command,
            timeout=2
        )

        # ----------------------------------------------------
        # WHTTP 설정 확인
        # ----------------------------------------------------

        if "OK" not in config_response:

            print("\n[FAIL] WHTTP 설정 실패")
            return

        # ----------------------------------------------------
        # HTTPS POST 실행
        # ----------------------------------------------------

        completed, response, rtt = execute_http(
            ser,
            timeout=RESPONSE_TIMEOUT
        )

        # ----------------------------------------------------
        # 결과 확인
        # ----------------------------------------------------

        if completed and check_ack(
            response,
            equip_id
        ):

            print("\n" + "=" * 60)
            print("전송 성공")
            print("=" * 60)

            print(f"equip_id       : {equip_id}")
            print(f"Payload        : {payload_bytes} bytes")
            print(f"RTT            : {rtt * 1000:.0f} ms")
            print("API ACK         : OK")

        else:

            print("\n" + "=" * 60)
            print("전송 실패")
            print("=" * 60)

            print(f"equip_id       : {equip_id}")
            print(f"Payload        : {payload_bytes} bytes")
            print(f"RTT            : {rtt * 1000:.0f} ms")

            print("\n[SERVER RESPONSE]")
            print(response)


if __name__ == "__main__":
    main()
import serial
import time


# ============================================================
# 설정
# ============================================================

PORT = "COM8"
BAUDRATE = 115200

# 우선 1회만 테스트
TEST_COUNT = 1

RESPONSE_TIMEOUT = 15

HOST = "ltop-pre-tb-api-server.onrender.com"
PATH = "/api/v1/tb/test-data"
PORT_HTTPS = 443


# ============================================================
# AT 명령 전송
# ============================================================

def send_command(ser, command, timeout=2):

    ser.reset_input_buffer()

    print(f"\n[SEND] {command}")

    ser.write((command + "\r\n").encode())
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

        if "\nOK" in response or "\nERROR" in response:
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

            # 정상 완료
            if "*WHTTPR:COMPLETED" in response:

                rtt = (
                    time.perf_counter()
                    - start_time
                )

                print("[RECV]")
                print(response.strip())

                return True, response, rtt

            # 실행 실패
            if "*WHTTPR:EXEC_FAILED" in response:

                rtt = (
                    time.perf_counter()
                    - start_time
                )

                print("[RECV]")
                print(response.strip())

                return False, response, rtt

        time.sleep(0.01)

    # Timeout
    rtt = (
        time.perf_counter()
        - start_time
    )

    print("[TIMEOUT]")
    print(response.strip())

    return False, response, rtt


# ============================================================
# API ACK 확인
# ============================================================

def check_ack(response, equip_id):

    expected_result = '"result":"OK"'
    expected_equip = f'"equip_id":"{equip_id}"'

    return (
        expected_result in response
        and expected_equip in response
    )


# ============================================================
# Main
# ============================================================

def main():

    success_count = 0
    fail_count = 0

    rtt_list = []
    failed_tests = []

    print("=" * 60)
    print("WD-L700K LTE TB 데이터 길이 테스트")
    print("5개 필드 전송")
    print("=" * 60)

    # ========================================================
    # 테스트 데이터
    # ========================================================

    site_id = 1
    equip_id = "TB001"

    bettery = 3.7
    inner_temp = 25.4
    corrol_volt = -920.5

    # ========================================================
    # 실제 전송 DATA 생성
    # ========================================================

    payload = (
        f"site_id={site_id}"
        f"&equip_id={equip_id}"
        f"&bettery={bettery}"
        f"&inner_temp={inner_temp}"
        f"&corrol_volt={corrol_volt}"
    )

    # WD-L700K에서 & 처리 문제 방지를 위해
    # 전체 DATA를 작은따옴표로 감싼다.
    data = f"'{payload}'"

    print("\n[PAYLOAD]")
    print(payload)

    print(
        f"\nPayload length : "
        f"{len(payload.encode('utf-8'))} bytes"
    )

    # ========================================================
    # Serial 연결
    # ========================================================

    with serial.Serial(
        port=PORT,
        baudrate=BAUDRATE,
        timeout=0.1
    ) as ser:

        time.sleep(1)

        # ----------------------------------------------------
        # LTE 상태 확인
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
        print("TB 데이터 전송 테스트 시작")
        print("=" * 60)

        total_start = time.perf_counter()

        # ====================================================
        # 전송
        # ====================================================

        for test_no in range(
            1,
            TEST_COUNT + 1
        ):

            print(
                f"\n[{test_no}/{TEST_COUNT}]"
            )

            # ------------------------------------------------
            # HTTP 설정
            # ------------------------------------------------

            command = (
                "AT*WHTTP=1,"
                "POST,"
                f"{HOST}"
                f"{PATH},"
                f"{PORT_HTTPS},,,"
                f"{data}"
            )

            config_response = send_command(
                ser,
                command,
                timeout=2
            )

            # ------------------------------------------------
            # HTTP 설정 결과 확인
            # ------------------------------------------------

            if "OK" not in config_response:

                print(
                    f"[FAIL] "
                    f"test={test_no} "
                    f"HTTP 설정 실패"
                )

                fail_count += 1
                failed_tests.append(test_no)

                continue

            # ------------------------------------------------
            # 실제 HTTPS 요청 실행
            # ------------------------------------------------

            completed, response, rtt = (
                execute_http(
                    ser,
                    timeout=RESPONSE_TIMEOUT
                )
            )

            # ------------------------------------------------
            # ACK 확인
            # ------------------------------------------------

            if (
                completed
                and check_ack(
                    response,
                    equip_id
                )
            ):

                success_count += 1
                rtt_list.append(rtt)

                print(
                    f"\n[SUCCESS] "
                    f"equip_id={equip_id} "
                    f"RTT={rtt * 1000:.0f} ms"
                )

            else:

                fail_count += 1
                failed_tests.append(test_no)

                print(
                    f"\n[FAIL] "
                    f"test={test_no} "
                    f"RTT={rtt * 1000:.0f} ms"
                )

        total_elapsed = (
            time.perf_counter()
            - total_start
        )

    # ========================================================
    # 결과
    # ========================================================

    print("\n")
    print("=" * 60)
    print("LTE TB 데이터 길이 테스트 결과")
    print("=" * 60)

    print(
        f"Payload       : "
        f"{len(payload.encode('utf-8'))} bytes"
    )

    print(
        f"총 송신       : "
        f"{TEST_COUNT}"
    )

    print(
        f"성공          : "
        f"{success_count}"
    )

    print(
        f"실패          : "
        f"{fail_count}"
    )

    success_rate = (
        success_count
        / TEST_COUNT
        * 100
    )

    print(
        f"성공률        : "
        f"{success_rate:.1f}%"
    )

    if rtt_list:

        avg_rtt = (
            sum(rtt_list)
            / len(rtt_list)
        )

        print(
            f"평균 RTT      : "
            f"{avg_rtt * 1000:.0f} ms"
        )

        print(
            f"최소 RTT      : "
            f"{min(rtt_list) * 1000:.0f} ms"
        )

        print(
            f"최대 RTT      : "
            f"{max(rtt_list) * 1000:.0f} ms"
        )

    print(
        f"전체 소요시간 : "
        f"{total_elapsed:.2f} sec"
    )

    print(
        f"요청당 총시간 : "
        f"{total_elapsed / TEST_COUNT:.3f} sec"
    )

    print(
        f"실패 Test     : "
        f"{failed_tests}"
    )

    print("=" * 60)


if __name__ == "__main__":
    main()
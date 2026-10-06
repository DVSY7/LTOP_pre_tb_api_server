import serial
import time

PORT = "COM8"
BAUDRATE = 115200

TEST_COUNT = 100
RESPONSE_TIMEOUT = 15


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


def execute_http(ser, timeout=15):

    ser.reset_input_buffer()

    print("[SEND] AT*WHTTP=3")

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

                rtt = (
                    time.perf_counter()
                    - start_time
                )

                print("[RECV]")
                print(response.strip())

                return True, response, rtt

            if "*WHTTPR:EXEC_FAILED" in response:

                rtt = (
                    time.perf_counter()
                    - start_time
                )

                print("[RECV]")
                print(response.strip())

                return False, response, rtt

        time.sleep(0.01)

    rtt = (
        time.perf_counter()
        - start_time
    )

    print("[TIMEOUT]")
    print(response.strip())

    return False, response, rtt


def check_ack(response, sequence):

    return (
        '"result":"OK"' in response
        and f'"sequence":{sequence}' in response
    )


def main():

    success_count = 0
    fail_count = 0

    rtt_list = []
    failed_sequences = []

    print("=" * 60)
    print("WD-L700K LTE 최적화 통신 시험")
    print("초기 설정 1회 + DATA만 변경")
    print("=" * 60)

    with serial.Serial(
        port=PORT,
        baudrate=BAUDRATE,
        timeout=0.1
    ) as ser:

        time.sleep(1)

        # ---------------------------------
        # 1. 기본 통신 상태 확인
        # ---------------------------------

        send_command(ser, "AT")
        send_command(ser, "AT+CGATT?")
        send_command(ser, "AT+CGACT?")
        send_command(ser, "AT+CGPADDR=1")

        # ---------------------------------
        # 2. HTTP 설정 - 최초 1회만
        # ---------------------------------

        print("\n" + "=" * 60)
        print("HTTP 기본 설정")
        print("=" * 60)

        initial_command = (
            "AT*WHTTP=1,"
            "POST,"
            "ltop-pre-tb-api-server.onrender.com"
            "/api/v1/tb/test,"
            "443"
        )

        response = send_command(
            ser,
            initial_command,
            timeout=2
        )

        if "OK" not in response:
            print("초기 HTTP 설정 실패")
            return

        # ---------------------------------
        # 3. 100회 시험
        # ---------------------------------

        print("\n" + "=" * 60)
        print("100회 최적화 테스트 시작")
        print("=" * 60)

        total_start = time.perf_counter()

        for sequence in range(
            1,
            TEST_COUNT + 1
        ):

            print(
                f"\n[{sequence}/{TEST_COUNT}]"
            )

            # -----------------------------
            # DATA만 변경
            # -----------------------------

            data = (
                f"'sequence={sequence}"
                f"&message=TEST'"
            )

            data_command = (
                f"AT*WHTTP=2,DATA,{data}"
            )

            config_response = send_command(
                ser,
                data_command,
                timeout=2
            )

            if "OK" not in config_response:

                print(
                    f"[FAIL] sequence={sequence} "
                    f"DATA 설정 실패"
                )

                fail_count += 1
                failed_sequences.append(sequence)

                continue

            # -----------------------------
            # HTTP 실행
            # -----------------------------

            completed, response, rtt = (
                execute_http(
                    ser,
                    timeout=RESPONSE_TIMEOUT
                )
            )

            if (
                completed
                and check_ack(
                    response,
                    sequence
                )
            ):

                success_count += 1
                rtt_list.append(rtt)

                print(
                    f"[SUCCESS] "
                    f"sequence={sequence} "
                    f"RTT={rtt * 1000:.0f} ms"
                )

            else:

                fail_count += 1
                failed_sequences.append(sequence)

                print(
                    f"[FAIL] "
                    f"sequence={sequence} "
                    f"RTT={rtt * 1000:.0f} ms"
                )

        total_elapsed = (
            time.perf_counter()
            - total_start
        )

    # ---------------------------------
    # 결과
    # ---------------------------------

    print("\n")
    print("=" * 60)
    print("LTE 최적화 통신 시험 결과")
    print("=" * 60)

    print(f"총 송신       : {TEST_COUNT}")
    print(f"성공          : {success_count}")
    print(f"실패          : {fail_count}")

    success_rate = (
        success_count / TEST_COUNT
    ) * 100

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
        f"실패 Sequence : "
        f"{failed_sequences}"
    )

    print("=" * 60)


if __name__ == "__main__":
    main()
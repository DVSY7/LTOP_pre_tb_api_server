"""Serial protocol and conservative server acknowledgement checks."""
from dataclasses import dataclass, asdict
import json
import math
import re
import time
from urllib.parse import urlencode


@dataclass(frozen=True)
class Settings:
    host: str = "ltop-pre-tb-api-server.onrender.com"
    path: str = "/api/v1/tb/data"
    port: int = 443
    equipment: str = "TB001"
    battery: float = 3.7
    temperature: float = 25.4
    voltage: float = -920.5
    humidity: float = 55.2
    timeout: float = 30.0
    interval: float = 1.0

    def validate(self):
        if not re.fullmatch(r"[A-Za-z0-9.-]+", self.host):
            raise ValueError("서버 주소에는 https:// 없이 호스트 이름만 입력하세요.")
        if not re.fullmatch(r"/[A-Za-z0-9/_\-.]*", self.path):
            raise ValueError("API 경로는 /로 시작하는 경로로 입력하세요.")
        if not 1 <= self.port <= 65535:
            raise ValueError("서버 포트는 1~65535 사이여야 합니다.")
        if not self.equipment.strip() or len(self.equipment) > 64:
            raise ValueError("장비 ID는 1~64자로 입력하세요.")
        if not all(math.isfinite(v) for v in (self.battery, self.temperature, self.voltage, self.humidity, self.timeout, self.interval)):
            raise ValueError("숫자 항목에는 유한한 숫자를 입력하세요.")
        if not 1 <= self.timeout <= 300 or not 0 <= self.interval <= 60:
            raise ValueError("응답 제한은 1~300초, 반복 간격은 0~60초로 입력하세요.")

    def command(self):
        self.validate()
        payload = urlencode({"e": self.equipment, "b": self.battery,
                             "t": self.temperature, "cv": self.voltage, "h": self.humidity})
        return f"AT*WHTTP=1,POST,{self.host}{self.path},{self.port},,,'{payload}'"


@dataclass
class Result:
    number: int
    timestamp: str
    seconds: float
    success: bool
    status: str
    row_id: str = ""
    detail: str = ""
    raw: str = ""
    demo: bool = False

    def record(self):
        return asdict(self)


@dataclass(frozen=True)
class Readiness:
    at: bool = False
    sim: str = "확인 대기"
    network: str = "확인 대기"
    packet: str = "확인 대기"
    signal: str = "미확인"
    ready: bool = False


def parse_readiness(sim_raw, network_raw, packet_raw, signal_raw):
    sim_match = re.search(r"(?m)^\s*\+CPIN:\s*([^\r\n]+)", sim_raw)
    sim = sim_match.group(1).strip() if sim_match and not has_error(sim_raw) else "미확인 / 명령 미지원"
    # Query response: +CEREG: <n>,<stat>[,...]. Unsolicited one-value
    # notifications do not prove that this query completed successfully.
    network_match = re.search(r"(?m)^\s*\+CEREG:\s*\d+\s*,\s*(\d+)", network_raw)
    status = int(network_match.group(1)) if network_match and not has_error(network_raw) else -1
    network = {0: "망 미등록", 1: "LTE 등록 완료", 2: "망 검색 중", 3: "등록 거절", 4: "상태 알 수 없음", 5: "LTE 등록 완료 (로밍)"}.get(status, "미확인 / 명령 미지원")
    packet_match = re.search(r"(?m)^\s*\+CGATT:\s*([01])\s*$", packet_raw)
    attached = packet_match.group(1) == "1" if packet_match and not has_error(packet_raw) else None
    packet = "데이터망 연결" if attached else "데이터망 미연결" if attached is False else "미확인 / 명령 미지원"
    signal_match = re.search(r"(?m)^\s*\+CSQ:\s*(\d+)\s*,", signal_raw)
    rssi = int(signal_match.group(1)) if signal_match and not has_error(signal_raw) else 99
    signal = f"{2*rssi-113} dBm (CSQ {rssi})" if 0 <= rssi <= 31 else "미확인"
    return Readiness(True, "SIM 준비 완료" if sim == "READY" else sim, network, packet, signal,
                     sim == "READY" and status in (1, 5) and attached is True)


def acknowledgements(raw):
    decoder = json.JSONDecoder()
    for match in re.finditer(r"\{", raw):
        try:
            value, _ = decoder.raw_decode(raw[match.start():])
        except ValueError:
            continue
        if isinstance(value, dict) and "result" in value:
            yield value


def has_error(raw):
    return bool(re.search(r"(?m)^\s*(?:ERROR|\+CM[ES] ERROR[^\r\n]*)\s*$", raw))


def classify(raw, equipment, seen_ids):
    for ack in acknowledgements(raw):
        row = ack.get("t_no")
        if ack.get("result") == "OK" and ack.get("equip_id") == equipment:
            if isinstance(row, int) and not isinstance(row, bool) and row > 0:
                if row in seen_ids:
                    return False, "중복 응답", str(row), "이미 확인한 저장 번호입니다. 새 저장 성공으로 집계하지 않습니다."
                seen_ids.add(row)
                return True, "DB 저장 확인", str(row), "서버가 DB 저장 완료와 저장 번호를 응답했습니다."
    if has_error(raw):
        return False, "모뎀 오류", "", "모뎀이 오류를 응답했습니다. 연결 및 AT 설정을 확인하세요."
    if re.search(r"HTTP/\d(?:\.\d)?\s+[45]\d\d|DB INSERT FAILED", raw):
        return False, "서버 오류", "", "서버가 요청 처리 오류를 응답했습니다."
    return False, "저장 미확인", "", "제한 시간 내 일치하는 DB 저장 응답을 확인하지 못했습니다. 실제 저장 여부는 알 수 없습니다."


class Modem:
    def __init__(self, serial_port, trace=lambda command, response: None):
        self.serial = serial_port
        self.trace = trace

    def exchange(self, command, timeout, expect_ack=False):
        self.serial.reset_input_buffer()
        self.serial.write((command + "\r\n").encode("utf-8"))
        self.serial.flush()
        end = time.monotonic() + timeout
        data = bytearray()
        while time.monotonic() < end:
            data.extend(self.serial.read(max(1, min(self.serial.in_waiting, 8192))))
            raw = data.decode("utf-8", errors="replace")
            if has_error(raw):
                break
            if expect_ack:
                if any(acknowledgements(raw)):
                    break
            elif re.search(r"(?m)^\s*OK\s*$", raw):
                break
            if len(data) > 262144:
                raise RuntimeError("모뎀 응답이 너무 큽니다. 통신 설정을 확인하세요.")
        raw = data.decode("utf-8", errors="replace")
        self.trace(command, raw)
        return raw

    def probe(self):
        raw = self.exchange("AT", 3)
        return bool(re.search(r"(?m)^\s*OK\s*$", raw)) and not has_error(raw)

    def readiness(self):
        if not self.probe():
            return Readiness(sim="AT 응답 없음", network="확인 불가", packet="확인 불가")
        responses = [self.exchange(command, 2) for command in
                     ("AT+CPIN?", "AT+CEREG?", "AT+CGATT?", "AT+CSQ")]
        return parse_readiness(*responses)

    def test(self, settings, number, seen_ids):
        started = time.monotonic()
        stamp = time.strftime("%Y-%m-%d %H:%M:%S")
        setup = self.exchange(settings.command(), min(settings.timeout, 5))
        if has_error(setup) or not re.search(r"(?m)^\s*OK\s*$", setup):
            return Result(number, stamp, time.monotonic() - started, False,
                          "요청 설정 실패", detail="모뎀이 전송 설정을 수락하지 않았습니다.", raw=setup)
        raw = self.exchange("AT*WHTTP=3", settings.timeout, expect_ack=True)
        success, status, row_id, detail = classify(raw, settings.equipment, seen_ids)
        return Result(number, stamp, time.monotonic() - started, success,
                      status, row_id, detail, setup + "\n" + raw)

import unittest
from modem_tester.core import Modem, Settings, classify, parse_readiness


class FakeSerial:
    def __init__(self, responses):
        self.responses = list(responses)
        self.buffer = bytearray()
        self.commands = []

    @property
    def in_waiting(self):
        return min(7, len(self.buffer))

    def reset_input_buffer(self):
        self.buffer.clear()

    def write(self, data):
        self.commands.append(data)
        self.buffer.extend(self.responses.pop(0).encode())

    def flush(self):
        pass

    def read(self, size):
        result = bytes(self.buffer[:size])
        del self.buffer[:size]
        return result


class ProtocolTests(unittest.TestCase):
    def test_fragmented_round_trip(self):
        port = FakeSerial(["AT\r\nOK\r\n", "OK\r\n", 'OK\r\nHTTP/1.1 200 OK\r\n{"result":"OK","equip_id":"TB001","t_no":123}\r\n'])
        modem = Modem(port)
        self.assertTrue(modem.probe())
        result = modem.test(Settings(), 1, set())
        self.assertTrue(result.success)
        self.assertEqual(result.row_id, "123")
        self.assertEqual(port.commands[-1], b"AT*WHTTP=3\r\n")

    def test_incomplete_or_wrong_ack_is_not_success(self):
        for raw in ["OK", "HTTP/1.1 200 OK", '{"result":"OK"}', '{"result":"OK","equip_id":"OTHER","t_no":1}', '{"result":"OK","equip_id":"TB001","t_no":true}']:
            with self.subTest(raw=raw):
                self.assertFalse(classify(raw, "TB001", set())[0])

    def test_duplicate_id(self):
        seen = set()
        raw = '{"result":"OK","equip_id":"TB001","t_no":5}'
        self.assertTrue(classify(raw, "TB001", seen)[0])
        self.assertEqual(classify(raw, "TB001", seen)[1], "중복 응답")

    def test_setup_failure_stops_request(self):
        port = FakeSerial(["\r\n+CME ERROR: 10\r\n"])
        result = Modem(port).test(Settings(), 1, set())
        self.assertFalse(result.success)
        self.assertEqual(len(port.commands), 1)

    def test_errors(self):
        self.assertEqual(classify("HTTP/1.1 500 Internal Server Error", "TB001", set())[1], "서버 오류")
        self.assertEqual(classify("\r\nERROR\r\n", "TB001", set())[1], "모뎀 오류")

    def test_settings(self):
        for settings in [Settings(host="bad\r\nAT"), Settings(port=0), Settings(timeout=float("nan")), Settings(interval=-1)]:
            with self.assertRaises(ValueError):
                settings.validate()
        self.assertIn("%26%27", Settings(equipment="장비&'1").command())

    def test_network_ready_and_roaming(self):
        for status in (1, 5):
            result = parse_readiness('+CPIN: READY\r\nOK', f'+CEREG: 2,{status},"1234","5678",7\r\nOK', '+CGATT: 1\r\nOK', '+CSQ: 20,99\r\nOK')
            self.assertTrue(result.ready)
            self.assertIn('-73 dBm', result.signal)

    def test_unknown_and_not_ready_states(self):
        for sim, network, packet in [('ERROR', '+CEREG: 0,1', '+CGATT: 1'), ('+CPIN: SIM PIN', '+CEREG: 0,1', '+CGATT: 1'), ('+CPIN: READY', '+CEREG: 0,2', '+CGATT: 1'), ('+CPIN: READY', '+CEREG: 0,1', '+CGATT: 0'), ('+CPIN: READY', '+CEREG: 1', '+CGATT: 1')]:
            with self.subTest(sim=sim, network=network, packet=packet):
                result = parse_readiness(sim, network, packet, '+CSQ: 99,99')
                self.assertFalse(result.ready)
                self.assertEqual(result.signal, '미확인')

    def test_readiness_uses_read_only_commands(self):
        port = FakeSerial(['OK\r\n', '+CPIN: READY\r\nOK\r\n', '+CEREG: 0,1\r\nOK\r\n', '+CGATT: 1\r\nOK\r\n', '+CSQ: 15,99\r\nOK\r\n'])
        self.assertTrue(Modem(port).readiness().ready)
        self.assertEqual(port.commands, [b'AT\r\n', b'AT+CPIN?\r\n', b'AT+CEREG?\r\n', b'AT+CGATT?\r\n', b'AT+CSQ\r\n'])


if __name__ == "__main__":
    unittest.main()

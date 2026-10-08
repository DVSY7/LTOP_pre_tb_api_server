import csv
import io
import time
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from app import Tester
from modem_tester.core import Readiness


class UITests(unittest.TestCase):
    def setUp(self):
        self.ports = patch('app.list_ports.comports', return_value=[])
        self.ports.start()
        self.dialog = patch('app.messagebox.showinfo')
        self.dialog.start()
        self.app = Tester(auto_monitor=False)
        self.app.withdraw()

    def tearDown(self):
        self.app.destroy()
        self.dialog.stop()
        self.ports.stop()

    def wait_idle(self):
        end = time.monotonic() + 12
        while self.app.busy and time.monotonic() < end:
            self.app.update()
            time.sleep(.01)
        self.assertFalse(self.app.busy)

    def test_demo_run_export_and_stop(self):
        app = self.app
        app.demo.set(True)
        app.demo_changed()
        self.wait_idle()
        self.assertTrue(app.ready)
        app.start()
        self.wait_idle()
        self.assertEqual(len(app.results), 10)
        self.assertEqual(app.metric_vars[1].get(), '90.0%')
        self.assertTrue(all(r.demo for r in app.results))
        app.results[0].raw = 'AT*WHTTP=3\r\nHTTP/1.1 200 OK\r\n{"result":"OK"}\r\n'
        output = io.StringIO()
        with patch('app.filedialog.asksaveasfilename', return_value='results.csv'), patch('app.open') as handle:
            handle.return_value.__enter__.return_value = output
            app.export()
        rows = list(csv.reader(io.StringIO(output.getvalue())))
        self.assertEqual(len(rows), 11)
        self.assertTrue(all(len(row) == 18 for row in rows))
        self.assertNotIn('AT원문', rows[0])
        self.assertNotIn('AT*WHTTP', output.getvalue())
        self.assertEqual(len(output.getvalue().splitlines()), 11)
        app.start()
        app.stop()
        self.wait_idle()
        self.assertLessEqual(len(app.results), 1)
        app.disconnect()
        self.assertFalse(app.ready)
        self.assertEqual(str(app.start_button['state']), 'disabled')

    def test_ready_gate_and_preview(self):
        app = self.app
        app.modem = SimpleNamespace(serial=SimpleNamespace(close=lambda: None))
        app.show_readiness(Readiness(at=True))
        self.assertEqual(str(app.start_button['state']), 'disabled')
        app.show_readiness(Readiness(True, 'SIM 준비 완료', 'LTE 등록 완료', '데이터망 연결', '-73 dBm', True))
        self.assertEqual(str(app.start_button['state']), 'normal')
        app.inputs['equipment'].set('NEW001')
        self.assertIn('NEW001', app.preview.get('1.0', 'end'))
        app.inputs['timeout'].set('invalid')
        self.assertNotIn('AT*WHTTP=1', app.preview.get('1.0', 'end'))

    def test_multiple_ports_require_selection_and_single_port_is_selected(self):
        with patch('app.list_ports.comports', return_value=[SimpleNamespace(device='COM4'), SimpleNamespace(device='COM5')]):
            self.app.refresh_ports()
            self.assertEqual(self.app.port.get(), '')
        with patch('app.list_ports.comports', return_value=[SimpleNamespace(device='COM4')]):
            self.app.refresh_ports()
            self.assertEqual(self.app.port.get(), 'COM4')

    def test_monitor_detects_removed_port(self):
        app = self.app
        app.port.set('COM4')
        app.modem = SimpleNamespace(serial=SimpleNamespace(close=lambda: None))
        app.ready = True
        app.monitor()
        self.assertIsNone(app.modem)
        self.assertFalse(app.ready)


if __name__ == '__main__':
    unittest.main()

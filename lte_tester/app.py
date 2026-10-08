"""Standalone LTE tester. Startup queries serial status, never the server/DB."""
import csv
import math
import queue
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

import serial
from serial.tools import list_ports

from modem_tester.core import Modem, Result, Settings, Readiness


class Tester(tk.Tk):
    def __init__(self, auto_monitor=True):
        super().__init__()
        self.title("PRE · LTE 통신 테스트 센터")
        self.geometry(f"{min(1280, self.winfo_screenwidth()-80)}x{min(760, self.winfo_screenheight()-100)}")
        self.minsize(640, 480)
        self.configure(bg="#f3f5fa")
        self.events = queue.Queue()
        self.stop_event = threading.Event()
        self.modem = None
        self.connected_demo = False
        self.busy = False
        self.closing = False
        self.ready = False
        self.auto_monitor = auto_monitor
        self.auto_connect = True
        self.next_check = 0.0
        self.last_ports = ()
        self.silent_job = False
        self.results = []
        self.seen_ids = set()
        self.inputs = {}
        self.locked_widgets = []
        self.demo = tk.BooleanVar(value=False)
        self.connection = tk.StringVar(value="연결 대기 · COM 포트를 선택하세요")
        self.summary = tk.StringVar(value="테스트를 시작하면 결과가 표시됩니다.")
        self.progress_text = tk.StringVar(value="테스트 대기 중")
        self.stage_vars = [tk.StringVar(value="확인 대기") for _ in range(5)]
        self.stage_vars[4].set("전송 후 확인")
        self.metric_vars = [tk.StringVar(value=v) for v in ("0 / 0", "—", "—", "0건")]
        self._build()
        self.refresh_ports()
        self.after(80, self.poll)
        if auto_monitor:
            self.after(700, self.monitor)
        self.protocol("WM_DELETE_WINDOW", self.close)

    def _build(self):
        from modem_tester.view import build_dashboard
        build_dashboard(self)

    def update_preview(self):
        if not hasattr(self, "preview") or len(self.inputs) != 10:
            return
        try:
            value = self.read_settings().command() + "\n\nAT*WHTTP=3"
        except ValueError:
            value = "입력값을 확인하면 AT 명령이 표시됩니다."
        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", value)
        self.preview.configure(state="disabled")

    def demo_changed(self):
        self.mode_label.configure(text="데모 · 가상 데이터" if self.demo.get() else "실제 장비 모드",
                                  bg="#fff1d6" if self.demo.get() else "#e4ebfa")
        self.auto_connect = True
        if self.demo.get() and not self.busy and not self.modem:
            self.connect()

    def port_selected(self):
        self.auto_connect = True
        self.next_check = 0
        if not self.busy and not self.modem:
            self.connect(automatic=True)

    def show_readiness(self, status):
        self.ready = status.ready
        values = ["AT 응답 정상" if status.at else "응답 미확인", status.sim, status.network, status.packet]
        for i, value in enumerate(values):
            self.stage_vars[i].set(value)
            good = [status.at, status.sim == "SIM 준비 완료", status.network.startswith("LTE 등록 완료"), status.packet == "데이터망 연결"][i]
            self.stage_labels[i].configure(foreground="#15835e" if good else "#b96821")
        text = "테스트 준비 완료" if status.ready else "테스트 준비 중 · SIM / LTE / 데이터망 상태를 확인하세요"
        text += f"  |  {self.port.get()}  ·  신호 {status.signal}  ·  {time.strftime('%H:%M:%S')} 확인"
        self.connection.set(text)
        self.controls()

    def monitor(self):
        if self.closing:
            return
        try:
            if not self.busy and not self.connected_demo:
                self.refresh_ports(quiet=True)
                if self.modem and self.port.get() not in self.last_ports:
                    self.disconnect(automatic=True)
                    self.connection.set("모뎀 연결이 해제되었습니다. USB 케이블을 확인하세요.")
                if time.monotonic() >= self.next_check:
                    if self.modem:
                        self.check_status()
                    elif self.auto_connect and self.port.get() and not self.demo.get():
                        self.connect(automatic=True)
        finally:
            self.after(2000, self.monitor)

    def check_status(self):
        if self.busy or not self.modem:
            return
        modem = self.modem
        self.launch(lambda: self.events.put(("readiness", modem.readiness())), silent=True)

    def text_tab(self, notebook, title):
        frame = ttk.Frame(notebook)
        notebook.add(frame, text=title)
        text = tk.Text(frame, wrap="word", height=7, font=("맑은 고딕", 10), state="disabled")
        scroll = ttk.Scrollbar(frame, command=text.yview)
        text.configure(yscrollcommand=scroll.set)
        scroll.pack(side="right", fill="y")
        text.pack(fill="both", expand=True)
        return text

    def append(self, widget, text):
        widget.configure(state="normal")
        widget.insert("end", text + "\n")
        if int(widget.index("end-1c").split(".")[0]) > 4000:
            widget.delete("1.0", "1001.0")
        widget.see("end")
        widget.configure(state="disabled")

    def log(self, text):
        self.append(self.log_text, f"[{time.strftime('%H:%M:%S')}] {text}")

    def refresh_ports(self, quiet=False):
        ports = [p.device for p in list_ports.comports()]
        self.port["values"] = ports
        if not self.modem and self.port.get() not in ports:
            self.port.set(ports[0] if len(ports) == 1 else "")
        changed = tuple(ports) != self.last_ports
        self.last_ports = tuple(ports)
        if changed or not quiet:
            self.log("사용 가능한 COM 포트: " + (", ".join(ports) or "없음. 모뎀 USB 케이블을 연결하세요."))
        if not self.modem and not self.connected_demo and not self.busy:
            self.connection.set("COM 포트를 선택하면 자동으로 상태를 확인합니다." if len(ports) > 1 else "모뎀 연결 대기 · COM 포트와 준비 상태를 자동 확인합니다.")

    def controls(self):
        connected = self.modem is not None or self.connected_demo
        for widget in (self.refresh_button, self.demo_check):
            widget.configure(state="disabled" if self.busy or connected else "normal")
        self.connect_button.configure(state="disabled" if self.busy or self.connected_demo else "normal")
        for widget in (self.port, self.baud):
            widget.configure(state="disabled" if self.busy or connected else "readonly")
        for widget in (self.disconnect_button, self.manual_button):
            widget.configure(state="normal" if connected and not self.busy else "disabled")
        self.start_button.configure(state="normal" if connected and self.ready and not self.busy else "disabled")
        for widget in self.locked_widgets + [self.count, self.manual]:
            widget.configure(state="disabled" if self.busy else "normal")
        self.export_button.configure(state="normal" if self.results and not self.busy else "disabled")

    def launch(self, work, silent=False):
        self.busy = True
        self.silent_job = silent
        self.controls()
        def wrapped():
            try:
                work()
            except Exception as exc:
                self.events.put(("error", str(exc)))
            finally:
                self.events.put(("idle", None))
        threading.Thread(target=wrapped, daemon=True).start()

    def connect(self, automatic=False):
        if self.busy:
            return
        if self.modem:
            self.check_status()
            return
        demo, port, baud = self.demo.get(), self.port.get(), int(self.baud.get())
        if not demo and not port:
            messagebox.showinfo("COM 포트 선택", "모뎀을 연결하고 COM 포트를 선택하세요.")
            return
        self.connection.set("모뎀 응답 확인 중…")
        def work():
            if demo:
                self.events.put(("connected", (None, "데모 모드 · 실제 모뎀 / 서버 / DB 연결 없음", None)))
                return
            device = serial.Serial(port, baud, timeout=0.1, write_timeout=3)
            modem = Modem(device, lambda cmd, raw: self.events.put(("raw", f"> {cmd}\n{raw or '(응답 없음)'}\n")))
            try:
                status = modem.readiness()
                if not status.at:
                    raise RuntimeError("포트는 열렸지만 AT 응답이 없습니다. 모뎀 포트와 통신 속도를 확인하세요.")
            except Exception:
                device.close()
                raise
            self.events.put(("connected", (modem, f"모뎀 연결 확인 · {port} / {baud} bps", status)))
        self.auto_connect = True
        self.launch(work, silent=automatic)

    def disconnect(self, automatic=False):
        if self.modem:
            self.modem.serial.close()
        self.modem = None
        self.connected_demo = False
        self.ready = False
        self.auto_connect = automatic
        for i in range(4):
            self.stage_vars[i].set("연결 대기")
            self.stage_labels[i].configure(foreground="#69778c")
        self.connection.set("연결 해제 · 다시 연결할 수 있습니다")
        self.controls()

    def read_settings(self):
        data = {key: value.get().strip() for key, value in self.inputs.items()}
        data["port"] = int(data["port"])
        for key in ("battery", "temperature", "voltage", "humidity", "timeout", "interval"):
            data[key] = float(data[key])
        settings = Settings(**data)
        settings.validate()
        return settings

    def start(self):
        if self.busy or not self.ready or not (self.modem or self.connected_demo):
            return
        try:
            settings = self.read_settings()
            count = int(self.count.get())
            if not 1 <= count <= 1000:
                raise ValueError("반복 횟수는 1~1000회로 입력하세요.")
        except ValueError as exc:
            messagebox.showerror("입력 확인", str(exc))
            return
        self.results.clear()
        self.table.delete(*self.table.get_children())
        self.stop_event.clear()
        self.progress.configure(maximum=count, value=0)
        self.planned = count
        self.run_settings = settings
        self.run_port = "DEMO" if self.connected_demo else self.port.get()
        self.run_baud = self.baud.get()
        demo = self.connected_demo
        self.summary.set("데모 실행 중 · 모든 결과는 가상 데이터입니다." if demo else "실제 LTE 전송 중 · 회차마다 DB에 데이터 1건을 저장합니다.")
        self.stage_vars[4].set("가상 결과 대기" if demo else "전송 후 확인")
        self.stage_labels[4].configure(foreground="#69778c")
        self.log(self.summary.get())
        self.update_metrics()
        self.draw_chart()
        def work():
            if not demo:
                status = self.modem.readiness()
                self.events.put(("readiness", status))
                if not status.ready:
                    self.events.put(("not_ready", None))
                    return
            for number in range(1, count + 1):
                if self.stop_event.is_set():
                    break
                self.events.put(("log", f"{number}/{count}회: " + ("가상 통신 진행 중" if demo else "모뎀에 요청을 전달하고 서버의 저장 응답을 기다립니다.")))
                if demo:
                    time.sleep(0.35)
                    success = number % 10 != 0
                    result = Result(number, time.strftime("%Y-%m-%d %H:%M:%S"), round(0.8 + abs(math.sin(number)) * 1.5, 3), success,
                                    "[데모] 저장 확인" if success else "[데모] 응답 미확인", str(10000 + number) if success else "",
                                    "가상 데이터 · 실제 전송 및 DB 저장 없음", demo=True)
                else:
                    started = time.monotonic()
                    try:
                        result = self.modem.test(settings, number, self.seen_ids)
                    except (serial.SerialException, OSError) as exc:
                        self.events.put(("result", Result(number, time.strftime("%Y-%m-%d %H:%M:%S"), time.monotonic()-started, False, "연결 끊김", detail="COM 연결이 끊겨 테스트를 종료했습니다.")))
                        self.events.put(("error", f"모뎀 연결이 끊겼습니다: {exc}"))
                        return
                self.events.put(("result", result))
                if number < count and self.stop_event.wait(0.15 if demo else settings.interval):
                    break
            self.events.put(("finished", self.stop_event.is_set()))
        self.launch(work)
        self.stop_button.configure(state="normal")

    def stop(self):
        self.stop_event.set()
        self.stop_button.configure(state="disabled")
        self.summary.set("중지 요청됨 · 현재 전송의 응답 또는 제한 시간까지 기다린 후 종료합니다.")
        self.log(self.summary.get())

    def send_manual(self):
        if self.busy or not (self.modem or self.connected_demo):
            return
        command = self.manual.get().strip()
        if not command.upper().startswith("AT") or any(c in command for c in "\r\n\x00"):
            messagebox.showerror("명령 확인", "AT로 시작하는 명령 한 줄을 입력하세요.")
            return
        if self.connected_demo:
            self.append(self.raw_text, f"[데모] > {command}\n실제 전송하지 않았습니다.")
            return
        def work():
            raw = self.modem.exchange(command, 5, expect_ack=True)
            self.events.put(("log", "직접 명령 전송을 마쳤습니다. 개발자용 AT 원문 탭에서 응답을 확인하세요." if raw else "직접 명령에 대한 응답이 없습니다."))
            self.events.put(("readiness", self.modem.readiness()))
        self.ready = False
        self.launch(work)

    def poll(self):
        try:
            for _ in range(100):
                kind, value = self.events.get_nowait()
                if kind == "raw":
                    self.append(self.raw_text, value)
                elif kind == "log":
                    self.log(value)
                elif kind == "connected":
                    self.modem, label, status = value
                    self.connected_demo = self.modem is None
                    self.connection.set(label)
                    self.log(label)
                    if status:
                        self.show_readiness(status)
                    else:
                        self.ready = True
                        for variable in self.stage_vars:
                            variable.set("데모 · 가상 상태")
                elif kind == "readiness":
                    self.show_readiness(value)
                elif kind == "not_ready":
                    self.summary.set("준비 상태가 바뀌어 전송하지 않았습니다. 연결 상태를 확인하세요.")
                    self.log(self.summary.get())
                elif kind == "result":
                    self.results.append(value)
                    item = self.table.insert("", "end", values=(value.number, value.timestamp, f"{value.seconds:.2f}초", value.status, value.row_id or "—", value.detail), tags=("ok" if value.success else "fail",))
                    self.table.see(item)
                    self.progress["value"] = len(self.results)
                    self.stage_vars[4].set(("[데모] " if value.demo else "") + ("DB 저장 확인" if value.success else "저장 미확인"))
                    self.stage_labels[4].configure(foreground="#15835e" if value.success else "#b96821")
                    self.log(f"{value.number}회: {value.status} · {value.seconds:.2f}초 · {value.detail}")
                    self.update_metrics()
                    self.draw_chart()
                elif kind == "finished":
                    ok = sum(r.success for r in self.results)
                    total = len(self.results)
                    prefix = "[데모 · 가상 결과] " if self.connected_demo else ""
                    report = f"{prefix}{'중지됨' if value else '테스트 완료'} · {total}회 중 저장 확인 {ok}건 / 미확인 {total-ok}건"
                    self.summary.set(report)
                    self.log(report)
                    if not self.closing:
                        messagebox.showinfo("테스트 평가", report + "\n\n미확인은 저장 실패를 확정하는 의미가 아닙니다.\n결과 CSV 저장 버튼으로 상세 결과를 보관할 수 있습니다.")
                elif kind == "error":
                    self.disconnect(automatic=self.silent_job)
                    self.connection.set("연결 확인 필요 · COM 포트와 모뎀 상태를 확인하세요")
                    self.summary.set("작업이 오류로 종료되었습니다. 완료된 결과는 CSV로 저장할 수 있습니다.")
                    self.log("작업을 진행하지 못했습니다. 개발자용 AT 원문에서 상세 오류를 확인하세요.")
                    self.append(self.raw_text, value)
                    if not self.closing and not self.silent_job:
                        messagebox.showerror("연결 / 통신 확인", "모뎀 연결 또는 통신 중 오류가 발생했습니다.\nCOM 포트가 다른 프로그램에서 사용 중인지, 케이블이 연결되어 있는지 확인하세요.\n상세 내용은 개발자용 AT 원문 탭에 표시됩니다.")
                elif kind == "idle":
                    self.busy = False
                    self.next_check = time.monotonic() + 12
                    self.stop_button.configure(state="disabled")
                    self.controls()
        except queue.Empty:
            pass
        if self.closing and not self.busy:
            self.disconnect()
            self.destroy()
            return
        self.after(80, self.poll)

    def update_metrics(self):
        count = len(self.results)
        ok = sum(r.success for r in self.results)
        values = [f"{count} / {getattr(self, 'planned', 0)}", f"{ok/count*100:.1f}%" if count else "—",
                  f"{sum(r.seconds for r in self.results)/count:.2f}초" if count else "—", f"{ok}건"]
        for variable, value in zip(self.metric_vars, values):
            variable.set(value)
        self.progress_text.set(f"{getattr(self, 'planned', 0)}회 중 {count}회 완료" + (" · 데모" if self.connected_demo else ""))

    def draw_chart(self):
        canvas = self.chart
        canvas.delete("all")
        width = max(canvas.winfo_width(), 300)
        chart_bottom = max(75, canvas.winfo_height() - 23)
        chart_top = 38
        plot_height = chart_bottom - chart_top
        canvas.create_text(12, 8, anchor="nw", width=width-24, text="회차별 왕복 처리 시간 (초) · 초록: 저장 확인 / 주황: 미확인" + (" · 데모 가상값" if self.connected_demo else ""), fill="#42526b")
        if not self.results:
            canvas.create_text(width / 2, (chart_top + chart_bottom)/2, text="테스트 시작 후 실시간 그래프가 표시됩니다.", fill="#78869b")
            return
        maximum = max(1, max(r.seconds for r in self.results)) * 1.15
        for i in range(3):
            y = chart_top + i * plot_height / 2
            canvas.create_line(55, y, width - 18, y, fill="#e8edf4")
            canvas.create_text(48, y, anchor="e", text=f"{maximum*(1-i/2):.1f}", fill="#78869b")
        previous = None
        for i, result in enumerate(self.results):
            x = 60 + i * (width - 85) / max(1, len(self.results) - 1)
            y = chart_bottom - result.seconds / maximum * plot_height
            if previous:
                canvas.create_line(*previous, x, y, fill="#7196b8", width=2)
            canvas.create_oval(x-3, y-3, x+3, y+3, fill="#16804a" if result.success else "#d27135", outline="")
            previous = (x, y)
        canvas.create_text(60, chart_bottom+15, text="1회", fill="#78869b")
        canvas.create_text(width-24, chart_bottom+15, anchor="e", text=f"{len(self.results)}회", fill="#78869b")

    def export(self):
        path = filedialog.asksaveasfilename(defaultextension=".csv", initialfile=f"LTE_{'DEMO_' if self.results[0].demo else ''}{time.strftime('%Y%m%d_%H%M%S')}.csv", filetypes=[("CSV 파일", "*.csv")])
        if not path:
            return
        try:
            with open(path, "w", newline="", encoding="utf-8-sig") as handle:
                writer = csv.writer(handle)
                writer.writerow(["모드", "회차", "시각", "처리시간(초)", "저장확인", "결과", "DB저장번호", "설명", "COM포트", "통신속도", "장비ID", "서버", "API경로", "서버포트", "배터리", "온도", "전위", "습도"])
                s = self.run_settings
                for r in self.results:
                    row = ["데모" if r.demo else "실제", r.number, r.timestamp, round(r.seconds, 3), "확인" if r.success else "미확인", r.status, r.row_id, r.detail, self.run_port, self.run_baud, s.equipment, s.host, s.path, s.port, s.battery, s.temperature, s.voltage, s.humidity]
                    writer.writerow([("'" + v) if isinstance(v, str) and v.startswith(("=", "+", "-", "@", "\t", "\r")) else v for v in row])
            self.log("결과 CSV를 저장했습니다: " + path)
        except OSError as exc:
            messagebox.showerror("저장 실패", str(exc))

    def close(self):
        self.closing = True
        if self.busy:
            self.stop()
            self.title("현재 통신 마무리 후 종료 중…")
        else:
            self.disconnect()
            self.destroy()


def main():
    import argparse
    parser = argparse.ArgumentParser(description="PRE LTE modem tester")
    parser.add_argument("--self-check", metavar="REPORT", help="Check packaged GUI dependencies without connecting a modem")
    args = parser.parse_args()
    if args.self_check:
        import json
        from pathlib import Path
        app = Tester(auto_monitor=False)
        app.withdraw()
        app.update_idletasks()
        report = {"startup": "OK", "tk": tk.TkVersion, "pyserial": serial.VERSION,
                  "command_preview": "AT*WHTTP=1" in app.preview.get("1.0", "end"),
                  "initial_start_disabled": str(app.start_button["state"]) == "disabled"}
        app.destroy()
        Path(args.self_check).write_text(json.dumps(report, indent=2), encoding="utf-8")
    else:
        Tester().mainloop()


if __name__ == "__main__":
    main()

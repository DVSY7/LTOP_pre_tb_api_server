"""Dashboard layout; all device operations live outside Tk's UI thread."""
import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont
from .core import Settings

BG = "#f3f5fa"
WHITE = "#ffffff"
INK = "#15243b"
MUTED = "#69778c"
BLUE = "#3268ed"


def build_dashboard(app):
    available = set(tkfont.families(app))
    app.ui_font = next((name for name in ("Malgun Gothic", "맑은 고딕", "Gulim") if name in available), "TkDefaultFont")
    style = ttk.Style(app)
    style.theme_use("clam")
    style.configure(".", font=("맑은 고딕", 10), background=WHITE, foreground=INK)
    style.configure("TFrame", background=WHITE)
    style.configure("Page.TFrame", background=BG)
    style.configure("TLabel", background=WHITE)
    style.configure("Muted.TLabel", foreground=MUTED)
    style.configure("Page.TLabel", background=BG)
    style.configure("TButton", padding=(10, 5), borderwidth=0, background="#e9eef8")
    style.map("TButton", background=[("active", "#dce5f7")], foreground=[("disabled", "#9aa5b5")])
    style.configure("Accent.TButton", background=BLUE, foreground=WHITE, font=("맑은 고딕", 11, "bold"))
    style.map("Accent.TButton", background=[("disabled", "#ced7ea"), ("active", "#2555cb")], foreground=[("disabled", "#7e8ba3")])
    style.configure("TEntry", padding=4, bordercolor="#dde3ed", lightcolor="#dde3ed", darkcolor="#dde3ed")
    style.configure("TCombobox", padding=4, bordercolor="#dde3ed", arrowsize=14)
    style.configure("TNotebook", borderwidth=0, tabmargins=0)
    style.layout("TNotebook.Tab", [("Notebook.tab", {"sticky": "nswe", "children": [
        ("Notebook.padding", {"side": "top", "sticky": "nswe", "children": [
            ("Notebook.label", {"side": "top", "sticky": "nswe"})]})]})])
    style.configure("TNotebook.Tab", padding=(10, 6), background="#e9eef8", borderwidth=0)
    style.map("TNotebook.Tab", background=[("selected", BLUE), ("active", "#dce5f7")],
              foreground=[("selected", WHITE), ("!selected", INK)],
              expand=[("selected", (0, 0, 0, 0)), ("!selected", (0, 0, 0, 0))],
              padding=[("selected", (10, 6)), ("!selected", (10, 6))])
    style.configure("Treeview", rowheight=32, borderwidth=0, fieldbackground=WHITE, background=WHITE, font=("맑은 고딕", 9))
    style.configure("Treeview.Heading", background="#edf2fb", padding=8, font=("맑은 고딕", 9, "bold"))
    style.configure("Horizontal.TProgressbar", background=BLUE, troughcolor="#e7ecf5", borderwidth=0, thickness=8)

    viewport = tk.Canvas(app, bg=BG, highlightthickness=0)
    scrollbar = ttk.Scrollbar(app, orient="vertical", command=viewport.yview)
    viewport.pack(side="left", fill="both", expand=True)
    viewport.configure(yscrollcommand=scrollbar.set)
    page = ttk.Frame(viewport, style="Page.TFrame", padding=12)
    window = viewport.create_window(0, 0, anchor="nw", window=page)
    app.page_viewport = viewport
    header = ttk.Frame(page, style="Page.TFrame")
    header.pack(fill="x", pady=(0, 8))
    app.title_label = ttk.Label(header, text="LTE 통신 테스트", style="Page.TLabel", font=(app.ui_font, 21, "normal"), padding=(0, 2, 0, 2))
    app.title_label.pack(side="left", pady=(4, 0))
    app.mode_label = tk.Label(header, text="실제 장비 모드", bg="#e4ebfa", fg=BLUE, padx=14, pady=7, font=("맑은 고딕", 10, "bold"))
    app.mode_label.pack(side="right")

    connect = ttk.Frame(page, padding=8)
    connect.pack(fill="x")
    ttk.Label(connect, text="장비 연결", font=("맑은 고딕", 11, "bold")).pack(side="left", padx=(0, 15))
    app.port = ttk.Combobox(connect, width=10, state="readonly")
    app.port.pack(side="left", padx=(0, 6))
    app.port.bind("<<ComboboxSelected>>", lambda event: app.port_selected())
    app.refresh_button = ttk.Button(connect, text="포트 검색", command=app.refresh_ports)
    app.refresh_button.pack(side="left")
    app.baud = ttk.Combobox(connect, values=[9600, 19200, 38400, 57600, 115200], width=8, state="readonly")
    app.baud.set("115200")
    app.baud.pack(side="left", padx=(12, 4))
    ttk.Label(connect, text="bps", style="Muted.TLabel").pack(side="left", padx=(0, 12))
    app.connect_button = ttk.Button(connect, text="연결 / 다시 확인", command=app.connect)
    app.connect_button.pack(side="left", padx=4)
    app.disconnect_button = ttk.Button(connect, text="연결 해제", command=app.disconnect, state="disabled")
    app.disconnect_button.pack(side="left", padx=4)
    app.demo_check = ttk.Checkbutton(connect, text="데모 · 실제 전송 없음", variable=app.demo, command=app.demo_changed)
    app.demo_check.pack(side="right")

    status = ttk.Frame(page, padding=(8, 5, 8, 5))
    status.pack(fill="x", pady=(1, 8))
    app.stage_labels = []
    for i, title in enumerate(("01  모뎀 응답", "02  SIM", "03  LTE 망", "04  데이터망", "05  서버 / DB")):
        cell = ttk.Frame(status)
        cell.grid(row=0, column=i, sticky="nsew", padx=(0, 12))
        status.columnconfigure(i, weight=1)
        ttk.Label(cell, text=title, style="Muted.TLabel", font=("맑은 고딕", 9)).pack(anchor="w")
        label = ttk.Label(cell, textvariable=app.stage_vars[i], font=("맑은 고딕", 10, "bold"))
        label.pack(anchor="w", pady=(5, 0))
        app.stage_labels.append(label)
    status_cells = list(status.winfo_children())
    connection_label = ttk.Label(status, textvariable=app.connection, foreground=BLUE)
    connection_label.grid(row=1, column=0, columnspan=5, sticky="w", pady=(5, 0))

    body = ttk.Frame(page, style="Page.TFrame")
    body.pack(fill="both", expand=True)
    left = ttk.Frame(body, padding=10)
    left.grid(row=0, column=0, sticky="nsew", padx=(0, 16))
    ttk.Label(left, text="전송 준비", font=("맑은 고딕", 15, "bold")).pack(anchor="w", pady=(0, 3))
    tabs = ttk.Notebook(left)
    app.settings_tabs = tabs
    tabs.pack(fill="both", expand=True)
    data = ttk.Frame(tabs, padding=(6, 8))
    comm = ttk.Frame(tabs, padding=(6, 8))
    advanced = ttk.Frame(tabs, padding=(6, 8))
    tabs.add(data, text="전송 데이터")
    tabs.add(comm, text="통신 설정")
    tabs.add(advanced, text="고급 AT")

    def field(parent, key, label, default, row, column=0, span=1):
        box = ttk.Frame(parent)
        box.grid(row=row, column=column, columnspan=span, sticky="ew", pady=(0, 6), padx=(0, 6))
        parent.columnconfigure(column, weight=1)
        ttk.Label(box, text=label, style="Muted.TLabel", font=("맑은 고딕", 9)).pack(anchor="w", pady=(0, 3))
        variable = tk.StringVar(value=str(default))
        entry = ttk.Entry(box, textvariable=variable, width=12)
        entry.pack(fill="x")
        app.inputs[key] = variable
        app.locked_widgets.append(entry)
        variable.trace_add("write", lambda *args: app.update_preview())

    field(data, "equipment", "장비 ID", "TB001", 0, span=2)
    field(data, "battery", "배터리 · V", 3.7, 1, 0)
    field(data, "temperature", "내부 온도 · ℃", 25.4, 1, 1)
    field(data, "voltage", "방식 전위 · mV", -920.5, 2, 0)
    field(data, "humidity", "내부 습도 · %", 55.2, 2, 1)
    field(comm, "host", "서버 주소 · https:// 제외", Settings.host, 0, span=2)
    field(comm, "path", "API 경로", Settings.path, 1, span=2)
    field(comm, "port", "HTTPS 포트", 443, 2, 0)
    field(comm, "timeout", "응답 제한 · 초", 30, 2, 1)
    ttk.Label(comm, text="전송 방식: AT*WHTTP / HTTPS POST", style="Muted.TLabel", font=("맑은 고딕", 9)).grid(row=3, column=0, columnspan=2, sticky="w")
    ttk.Label(advanced, text="생성된 전송 명령 · 읽기 전용", style="Muted.TLabel").pack(anchor="w")
    app.preview = tk.Text(advanced, width=24, height=3, wrap="char", font=("Consolas", 9), bg="#f3f6fc", relief="flat", padx=8, pady=8, state="disabled")
    app.preview.pack(fill="x", pady=(4, 6))
    ttk.Label(advanced, text="직접 AT 명령", style="Muted.TLabel").pack(anchor="w")
    app.manual = ttk.Entry(advanced)
    app.manual.insert(0, "AT+CSQ")
    app.manual.pack(fill="x", pady=7)
    app.manual_button = ttk.Button(advanced, text="명령 전송", command=app.send_manual, state="disabled")
    app.manual_button.pack(fill="x")

    ttk.Separator(left).pack(fill="x", pady=6)
    plan = ttk.Frame(left)
    plan.pack(fill="x")
    count_box = ttk.Frame(plan)
    count_box.grid(row=0, column=0, sticky="ew", padx=(0, 12))
    ttk.Label(count_box, text="반복 횟수", style="Muted.TLabel", font=("맑은 고딕", 9)).pack(anchor="w", pady=(0, 3))
    app.count = ttk.Combobox(count_box, values=[10, 50, 100], width=9)
    app.count.set("10")
    app.count.pack(fill="x")
    field(plan, "interval", "반복 간격 · 초", 1, 0, 1)
    plan.columnconfigure(0, weight=1)
    actions = ttk.Frame(left)
    actions.pack(fill="x", pady=(2, 0))
    app.start_button = ttk.Button(actions, text="테스트 시작", style="Accent.TButton", command=app.start, state="disabled")
    app.start_button.pack(side="left", fill="x", expand=True, padx=(0, 6))
    app.stop_button = ttk.Button(actions, text="테스트 중지", command=app.stop, state="disabled")
    app.stop_button.pack(side="left", fill="x", expand=True)

    right = ttk.Frame(body, style="Page.TFrame")
    right.grid(row=0, column=1, sticky="nsew")
    body.columnconfigure(1, weight=1)
    metrics = ttk.Frame(right, style="Page.TFrame")
    metrics.pack(fill="x", pady=(0, 6))
    for i, title in enumerate(("완료 / 계획", "DB 저장 확인율", "평균 처리 시간", "저장 확인")):
        card = ttk.Frame(metrics, padding=5)
        card.grid(row=0, column=i, sticky="nsew", padx=(0, 8 if i < 3 else 0))
        metrics.columnconfigure(i, weight=1, uniform="metric")
        ttk.Label(card, text=title, style="Muted.TLabel", font=("맑은 고딕", 9)).pack(anchor="w")
        ttk.Label(card, textvariable=app.metric_vars[i], font=("맑은 고딕", 18, "bold"), foreground=BLUE).pack(anchor="w", pady=(2, 0))
    progress_box = ttk.Frame(right, padding=5)
    progress_box.pack(fill="x", pady=(0, 6))
    ttk.Label(progress_box, textvariable=app.progress_text, font=("맑은 고딕", 11, "bold")).pack(side="left", padx=(0, 12))
    app.progress = ttk.Progressbar(progress_box, length=100)
    app.progress.pack(side="left", fill="x", expand=True)
    app.chart = tk.Canvas(right, height=110, background=WHITE, highlightthickness=0)
    app.chart.pack(fill="x")
    app.chart.bind("<Configure>", lambda event: app.draw_chart())
    summary_label = ttk.Label(right, textvariable=app.summary, style="Page.TLabel", wraplength=720, font=("맑은 고딕", 9))
    summary_label.pack(anchor="w", pady=5)
    notebook = ttk.Notebook(right, height=90)
    app.result_tabs = notebook
    notebook.pack(fill="both", expand=True)
    results = ttk.Frame(notebook)
    notebook.add(results, text="회차별 결과")
    columns = ("number", "time", "seconds", "status", "row", "detail")
    app.table = ttk.Treeview(results, columns=columns, show="headings", height=5)
    for key, title, width in zip(columns, ("회차", "시각", "처리 시간", "결과", "저장 번호", "설명"), (45, 145, 85, 130, 85, 350)):
        app.table.heading(key, text=title)
        app.table.column(key, width=width, minwidth=40, stretch=key == "detail")
    vertical = ttk.Scrollbar(results, command=app.table.yview)
    horizontal = ttk.Scrollbar(results, orient="horizontal", command=app.table.xview)
    app.table.configure(yscrollcommand=vertical.set, xscrollcommand=horizontal.set)
    results.rowconfigure(0, weight=1)
    results.columnconfigure(0, weight=1)
    app.table.grid(row=0, column=0, sticky="nsew")
    vertical.grid(row=0, column=1, sticky="ns")
    horizontal.grid(row=1, column=0, sticky="ew")
    app.table.tag_configure("ok", foreground="#15835e")
    app.table.tag_configure("fail", foreground="#b96821")
    app.log_text = app.text_tab(notebook, "한글 진행 로그")
    app.raw_text = app.text_tab(notebook, "AT 원문")
    footer = ttk.Frame(right, style="Page.TFrame")
    footer.pack(fill="x", pady=(5, 0))
    app.export_button = ttk.Button(footer, text="결과 CSV 저장", command=app.export, state="disabled")
    app.export_button.pack(side="right")
    ttk.Label(footer, text="저장 확인율은 서버 응답 기준입니다.\n처리 시간은 AT 설정부터 응답까지 측정합니다.", style="Page.TLabel", foreground=MUTED, font=("맑은 고딕", 9)).pack(side="left")
    app.layout_mode = None
    connection_widgets = list(connect.winfo_children())
    for widget in connection_widgets:
        widget.pack_forget()
    metric_cards = list(metrics.winfo_children())
    pending = {"layout": None, "scroll": None}

    def schedule_layout(event=None):
        if pending["layout"] is None:
            pending["layout"] = app.after_idle(reflow)

    def schedule_scroll(event=None):
        if pending["scroll"] is None:
            pending["scroll"] = app.after_idle(sync_scroll)

    def reflow(event=None):
        pending["layout"] = None
        # Before Map, Tk reports 1x1. Never persist a layout based on that
        # temporary size; Map/Configure will schedule the real first layout.
        if not viewport.winfo_ismapped() or viewport.winfo_width() <= 1:
            return
        width = viewport.winfo_width()
        viewport.itemconfigure(window, width=width)
        narrow = width < 1000
        app.layout_mode = "stacked" if narrow else "columns"
        left.grid_configure(row=0, column=0, padx=(0, 0 if narrow else 16), pady=(0, 14 if narrow else 0))
        right.grid_configure(row=1 if narrow else 0, column=0 if narrow else 1)
        body.columnconfigure(0, weight=1 if narrow else 0, minsize=0 if narrow else 330)
        body.columnconfigure(1, weight=0 if narrow else 1)
        body.rowconfigure(0, weight=0 if narrow else 1)
        body.rowconfigure(1, weight=1 if narrow else 0)
        # Keep the controls in their actual parent. Sibling row frames can
        # cover widgets packed with in_= even when geometry checks pass.
        available_width = max(300, width-48)
        control_columns = 9 if width >= 1000 else 3
        for i, widget in enumerate(connection_widgets):
            widget.grid(row=i//control_columns, column=i%control_columns,
                        sticky="w", padx=(0, 8), pady=2)
        cols = 3 if narrow else 5
        for i in range(5):
            status.columnconfigure(i, weight=1 if i < cols else 0, uniform="stage" if i < cols else "")
        for i, cell in enumerate(status_cells):
            cell.grid_configure(row=i//cols, column=i%cols, pady=(0, 8))
            app.stage_labels[i].configure(wraplength=max(140, int(available_width/cols)-20))
        connection_label.grid_configure(row=(4//cols)+1, columnspan=cols)
        connection_label.configure(wraplength=available_width)
        summary_label.configure(wraplength=max(300, width-(80 if narrow else 420)))
        metric_columns = 2 if width < 760 else 4
        for i in range(4):
            metrics.columnconfigure(i, weight=1 if i < metric_columns else 0, uniform="metric" if i < metric_columns else "")
        for i, card in enumerate(metric_cards):
            card.grid_configure(row=i//metric_columns, column=i%metric_columns, pady=(0, 6))
        # Grid/pack request sizes settle at idle, after the changes above.
        # Reading reqheight here would use the previous (possibly stacked) layout.
        schedule_scroll()

    def sync_scroll(event=None):
        if not viewport.winfo_ismapped() or viewport.winfo_height() <= 1:
            pending["scroll"] = None
            return
        # Drain geometry requests before reading the new natural height.
        # Keep the job marked pending to avoid reentrant scroll callbacks.
        pending["scroll"] = "settling"
        page.update_idletasks()
        required = page.winfo_reqheight()
        needs_scroll = required > viewport.winfo_height() + 1
        if needs_scroll and not scrollbar.winfo_manager():
            scrollbar.pack(side="right", fill="y", before=viewport)
        elif not needs_scroll and scrollbar.winfo_manager():
            scrollbar.pack_forget()
            viewport.yview_moveto(0)
        height = max(required, viewport.winfo_height())
        viewport.itemconfigure(window, height=height)
        viewport.configure(scrollregion=(0, 0, viewport.winfo_width(), height))
        pending["scroll"] = None

    def wheel(event):
        if isinstance(event.widget, (tk.Text, ttk.Treeview, ttk.Combobox)):
            return
        viewport.yview_scroll(-int(event.delta/120), "units")
        return "break"

    viewport.bind("<Map>", schedule_layout)
    viewport.bind("<Configure>", schedule_layout)
    page.bind("<Configure>", schedule_scroll)
    app.bind("<MouseWheel>", wheel, add="+")
    app.reflow_layout = reflow
    schedule_layout()
    app.update_preview()

"""Mapped-window geometry checks. No serial connection or server traffic."""
from pathlib import Path
import sys
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import Tester


def main():
    with patch('app.list_ports.comports', return_value=[]):
        app = Tester(auto_monitor=False)
    app.attributes('-alpha', 0)
    try:
        # First paint must settle without wheel events or a manual reflow.
        app.update()
        viewport = app.page_viewport
        assert app.layout_mode == ('columns' if viewport.winfo_width() >= 1000 else 'stacked')
        assert viewport.yview()[0] == 0.0
        if viewport.winfo_width() >= 1000:
            assert viewport.yview() == (0.0, 1.0), ('startup scroll', viewport.yview())
        assert app.port.winfo_ismapped()
        assert app.export_button.winfo_ismapped()
        print('PASS first paint: no scrolling or manual reflow needed')
        for width, height in ((1280, 760), (1100, 668), (1920, 1000), (900, 650), (640, 480)):
            app.geometry(f'{width}x{height}')
            app.update()
            expected = 'columns' if width >= 1000 else 'stacked'
            assert app.layout_mode == expected, (width, app.layout_mode)
            viewport = app.page_viewport
            bounds = tuple(float(v) for v in viewport.cget('scrollregion').split())
            assert bounds[3] >= viewport.winfo_height()
            if expected == 'columns':
                assert bounds[3] <= viewport.winfo_height() + 1, (width, height, 'unnecessary page scroll', bounds, viewport.winfo_height())
            for widget in (app.port, app.baud, app.refresh_button, app.start_button, app.stop_button, app.demo_check, app.connect_button, app.export_button, app.chart):
                if expected == 'columns':
                    assert widget.winfo_ismapped(), (width, str(widget), 'not visible')
                x = widget.winfo_rootx() - viewport.winfo_rootx()
                assert x >= 0 and x + widget.winfo_width() <= viewport.winfo_width(), (width, str(widget), x, widget.winfo_width(), viewport.winfo_width())
            for notebook in (app.settings_tabs, app.result_tabs):
                size = (notebook.winfo_width(), notebook.winfo_height())
                for tab in notebook.tabs():
                    notebook.select(tab)
                    app.update()
                    assert size == (notebook.winfo_width(), notebook.winfo_height()), (width, tab, size, notebook.winfo_height())
            viewport.yview_moveto(1)
            app.update()
            assert app.export_button.winfo_ismapped()
            bottom = app.export_button.winfo_rooty() + app.export_button.winfo_height()
            assert bottom <= viewport.winfo_rooty() + viewport.winfo_height(), (width, bottom)
            viewport.yview_moveto(0)
            print(f'PASS {width}x{height}: {expected}, controls reachable, stable tabs')
    finally:
        app.destroy()


if __name__ == '__main__':
    main()

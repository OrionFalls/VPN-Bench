from pathlib import Path


def test_ui_uses_external_javascript():
    ui = Path(__file__).parents[1] / "app" / "vpn_bench" / "ui.py"
    js = Path(__file__).parents[1] / "app" / "vpn_bench" / "static" / "app.js"
    source = ui.read_text(encoding="utf-8")
    script = js.read_text(encoding="utf-8")

    assert '<script src="/static/app.js" defer></script>' in source
    assert "<script>" not in source
    assert len(script) > 1000
    assert "function nav()" in script
    assert "function boot()" in script

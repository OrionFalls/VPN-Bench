from pathlib import Path


def test_ui_uses_external_assets():
    root = Path(__file__).parents[1]
    ui = root / "app" / "vpn_bench" / "ui.py"
    js = root / "app" / "vpn_bench" / "static" / "app.js"
    css = root / "app" / "vpn_bench" / "static" / "app.css"
    source = ui.read_text(encoding="utf-8")
    script = js.read_text(encoding="utf-8")
    styles = css.read_text(encoding="utf-8")

    assert '<link rel="stylesheet" href="/static/app.css">' in source
    assert '<script src="/static/app.js" defer></script>' in source
    assert "<script>" not in source
    assert "<style>" not in source
    assert len(script) > 1000
    assert len(styles) > 3000
    assert "function nav()" in script
    assert "function boot()" in script
    assert "@media (max-width:700px)" in styles
    assert ".stats .card strong" in styles

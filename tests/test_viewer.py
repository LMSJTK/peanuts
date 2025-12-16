from __future__ import annotations

import socket
import subprocess
import sys
import time
from pathlib import Path

import pytest

playwright = pytest.importorskip("playwright.sync_api")
from playwright.sync_api import Error as PlaywrightError, sync_playwright  # type: ignore  # noqa: E402

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _reserve_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("", 0))
        return sock.getsockname()[1]


@pytest.fixture(scope="session")
def e2e_artifacts() -> dict[str, Path]:
    subprocess.run(
        [sys.executable, "scripts/run_e2e.py", "--seed", "42"],
        cwd=PROJECT_ROOT,
        check=True,
    )
    return {
        "replay": PROJECT_ROOT / "tmp/e2e/replay_log.json",
    }


def test_viewer_renders_replay_without_console_errors(e2e_artifacts: dict[str, Path]) -> None:
    port = _reserve_port()
    server = subprocess.Popen(
        [sys.executable, "-m", "http.server", str(port)],
        cwd=PROJECT_ROOT,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    try:
        time.sleep(0.5)
        with sync_playwright() as playwright_ctx:
            try:
                browser = playwright_ctx.chromium.launch(headless=True)
            except PlaywrightError as exc:  # pragma: no cover - dependency guard
                pytest.skip(f"Playwright browser unavailable: {exc}")

            page = browser.new_page()
            console_messages = []
            page.on("console", lambda msg: console_messages.append(msg))

            page.goto(
                f"http://localhost:{port}/web/index.html?artifact=tmp/e2e/replay_log.json",
                wait_until="networkidle",
            )
            page.wait_for_selector("#feedStatus", timeout=5000)
            page.wait_for_timeout(500)

            status_text = page.text_content("#feedStatus") or ""
            errors = [msg for msg in console_messages if msg.type == "error"]

            assert "Loaded" in status_text
            assert not errors, "Viewer emitted console errors while rendering replay"
    finally:
        server.terminate()
        try:
            server.wait(timeout=5)
        except subprocess.TimeoutExpired:  # pragma: no cover - cleanup guard
            server.kill()

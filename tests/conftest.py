import os
import socket
import subprocess
import sys
import time
from pathlib import Path
import httpx
import pytest

ROOT = Path(__file__).resolve().parents[1]


class Server:
    def __init__(self, directory):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            self.port = sock.getsockname()[1]
        self.url = f"http://127.0.0.1:{self.port}"
        self.env = {**os.environ, "OPENAI_API_KEY": "fixture-openai", "OPENAI_MENU_MODEL": "gpt-6-luna", "OPENAI_IMAGE_MODEL": "gpt-image-2.5-flare",
                    "DATA_DIR": str(directory), "FIXTURE_PORT": str(self.port), "SECURE_COOKIES": "false"}
        self.process = None

    def start(self):
        self.process = subprocess.Popen([sys.executable, "tests/fixture_server.py"], cwd=ROOT, env=self.env)
        for _ in range(100):
            try:
                if httpx.get(self.url + "/api/health").status_code == 200: return
            except httpx.TransportError:
                pass
            if self.process.poll() is not None: raise RuntimeError("Fixture server exited")
            time.sleep(.05)
        raise RuntimeError("Fixture server did not start")

    def stop(self):
        if self.process:
            self.process.terminate()
            self.process.wait(timeout=10)

    def restart(self):
        self.stop()
        self.start()


@pytest.fixture(scope="session")
def server(tmp_path_factory):
    instance = Server(tmp_path_factory.mktemp("snapmenu"))
    instance.start()
    yield instance
    instance.stop()


@pytest.fixture
def phone(browser, server):
    context = browser.new_context(viewport={"width": 390, "height": 844}, device_scale_factor=1, is_mobile=True, has_touch=True)
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    with page.expect_response("**/api/menus/latest"):
        page.goto(server.url)
    yield page
    context.close()
    assert not errors, errors

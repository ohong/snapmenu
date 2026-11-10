import os
import socket
import subprocess
import time
from pathlib import Path
import httpx
import pytest

ROOT = Path(__file__).resolve().parents[1]


class Server:
    def __init__(self, provider):
        with socket.socket() as sock:
            sock.bind(("127.0.0.1", 0))
            self.port = sock.getsockname()[1]
        self.url = f"http://127.0.0.1:{self.port}"
        self.provider = provider

    def start(self):
        self.process = subprocess.Popen(
            ["node", "tests/runtime.mjs"],
            cwd=ROOT,
            env={
                **os.environ,
                "FIXTURE_PORT": str(self.port),
                "TEST_PROVIDER": self.provider,
            },
            stdout=subprocess.DEVNULL,
        )
        for _ in range(100):
            try:
                if httpx.get(self.url + "/api/health").status_code == 200:
                    return
            except httpx.TransportError:
                pass
            if self.process.poll() is not None:
                raise RuntimeError("Fixture exited")
            time.sleep(0.1)
        raise RuntimeError("Fixture did not start")

    def stop(self):
        self.process.terminate()
        self.process.wait(timeout=15)


@pytest.fixture(scope="session", params=["muse", "openai"])
def server(request):
    instance = Server(request.param)
    instance.start()
    yield instance
    instance.stop()


@pytest.fixture
def phone(browser, server):
    context = browser.new_context(
        viewport={"width": 390, "height": 844}, is_mobile=True, has_touch=True
    )
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(server.url)
    yield page
    context.close()
    assert not errors, errors

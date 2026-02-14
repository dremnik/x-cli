import http.client
import socket
import threading
import time

from pytest import MonkeyPatch

from xcli.core.config import Settings
from xcli.core.x_auth import run_login, wait_for_callback


def _reserve_port() -> int:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.bind(("127.0.0.1", 0))
    port = int(sock.getsockname()[1])
    sock.close()
    return port


def _send_get(port: int, path: str) -> None:
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=2)
    conn.request("GET", path)
    response = conn.getresponse()
    response.read()
    conn.close()


def test_wait_for_callback_accepts_later_matching_path() -> None:
    port = _reserve_port()
    redirect_uri = f"http://127.0.0.1:{port}/callback"

    def sender() -> None:
        time.sleep(0.05)
        _send_get(port, "/health")
        time.sleep(0.05)
        _send_get(port, "/callback?code=abc")

    worker = threading.Thread(target=sender, daemon=True)
    worker.start()

    callback = wait_for_callback(redirect_uri, timeout_sec=2)
    worker.join(timeout=1)

    assert callback.endswith("/callback?code=abc")


def test_run_login_does_not_open_browser_unless_requested(monkeypatch: MonkeyPatch) -> None:
    opened: list[str] = []

    class FakeClient:
        def get_authorization_url(self) -> str:
            return "https://example.com/auth"

        def fetch_token(self, authorization_response: str) -> dict[str, str]:
            assert "code=ok" in authorization_response
            return {"access_token": "token"}

    def fake_make_oauth_client(settings: Settings) -> FakeClient:
        del settings
        return FakeClient()

    def fake_wait_for_callback(redirect_uri: str, timeout_sec: int = 300) -> str:
        del timeout_sec
        return f"{redirect_uri}?code=ok"

    def fake_open(url: str) -> bool:
        opened.append(url)
        return True

    monkeypatch.setattr("xcli.core.x_auth.make_oauth_client", fake_make_oauth_client)
    monkeypatch.setattr("xcli.core.x_auth.wait_for_callback", fake_wait_for_callback)
    monkeypatch.setattr("xcli.core.x_auth.webbrowser.open", fake_open)

    settings = Settings(
        client_id="cid",
        client_secret="",
        redirect_uri="http://127.0.0.1:3000/callback",
        scopes=("tweet.read",),
    )

    token = run_login(settings, open_browser=False)
    assert token["access_token"] == "token"
    assert opened == []

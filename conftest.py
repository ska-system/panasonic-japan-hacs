"""Pytest configuration for Windows asyncio compatibility."""
import sys
from pathlib import Path
import pytest
from pytest_socket import enable_socket, socket_allow_hosts

stubs_path = Path(__file__).parent / "tests" / "stubs"
sys.path.insert(0, str(stubs_path))

def pytest_sessionstart(session: pytest.Session) -> None:
    """Enable socket access at session start to support Windows asyncio initialization."""
    try:
        enable_socket()
        socket_allow_hosts(["127.0.0.1", "localhost", "::1"], allow_unix_socket=True)
    except Exception:
        pass

@pytest.fixture(autouse=True, scope="session")
def _force_enable_socket_for_windows():
    """Windows環境のイベントループが使用するソケットを強制許可する"""
    try:
        enable_socket()
    except Exception:
        pass
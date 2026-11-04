import hashlib
import asyncio
import json
import os
import stat
import sys
from contextlib import asynccontextmanager
from pathlib import Path

import asyncssh
import pytest
import pytest_asyncio

from remote_logs import core
from remote_logs.core import DOWNLOAD_LIMIT, Logs, relative
from remote_logs.security import protect, unprotect
from remote_logs.server import build


class PasswordServer(asyncssh.SSHServer):
    def begin_auth(self, username):
        return True

    def password_auth_supported(self):
        return True

    def validate_password(self, username, password):
        return username == "reader" and password == "test-only-password"


@pytest_asyncio.fixture
async def service(tmp_path, monkeypatch):
    remote = tmp_path / "remote"
    (remote / "logs" / "nested").mkdir(parents=True)
    (remote / "logs" / "app.log").write_bytes(b"start\nERROR request ABC123\nstack trace\ndone\n")
    (remote / "logs" / "nested" / "batch.log").write_bytes(b"batch error\n")
    (remote / "outside.txt").write_text("secret")
    key = asyncssh.generate_private_key("ssh-ed25519")
    class ReadAuditSFTP(asyncssh.SFTPServer):
        def open(self, path, pflags, attrs):
            # Actual on-wire open requests must never request creation/write/truncation.
            assert not pflags & (asyncssh.FXF_WRITE | asyncssh.FXF_APPEND | asyncssh.FXF_CREAT | asyncssh.FXF_TRUNC)
            return super().open(path, pflags, attrs)

    server = await asyncssh.create_server(PasswordServer, "127.0.0.1", 0,
        server_host_keys=[key], sftp_factory=lambda chan: ReadAuditSFTP(chan, chroot=str(remote)),
        encoding=None)
    hostfile = tmp_path / "known_hosts"
    hostfile.write_bytes(f"[127.0.0.1]:{server.get_port()} ".encode() + key.export_public_key())
    config = {"download_directory": "downloads", "environments": {"test": {
        "host": "127.0.0.1", "port": server.get_port(), "username": "reader",
        "password_dpapi": protect("test-only-password") if os.name == "nt" else "test-encrypted-placeholder", "known_hosts": str(hostfile),
        "roots": {"app": "/logs"}}}}
    config_path = tmp_path / "config.json"
    config_path.write_text(json.dumps(config))
    monkeypatch.setattr(core, "unprotect", lambda _: "test-only-password")
    logs = Logs(str(config_path))
    yield logs, remote, config_path
    server.close()
    await server.wait_closed()


async def invoke(logs, op, **kwargs):
    return await logs.call(op, environment="test", root="app", **kwargs)


@pytest.mark.parametrize("path", ["../outside.txt", "/outside.txt", "nested/../../x", "x\\y", "x\x00y"])
def test_reject_paths(path):
    with pytest.raises(ValueError):
        relative(path)


async def test_real_sftp_all_six_tools(service):
    logs, remote, _ = service
    before = (remote / "logs" / "app.log").read_bytes()
    assert "password" not in json.dumps(logs.list_servers())
    listing = await invoke(logs, "list_directory", limit=1)
    assert len(listing["entries"]) == 1 and listing["next_offset"] == 1
    found = await invoke(logs, "find_files")
    assert len(found["files"]) == 2
    read = await invoke(logs, "read_log", path="app.log")
    assert "ABC123" in read["text"]
    tail = await invoke(logs, "read_log", path="app.log", max_bytes=5, tail=True)
    assert tail["text"] == "done\n"
    search = await invoke(logs, "search_logs", paths=["app.log"], text="abc123", case_sensitive=False)
    assert search["matches"][0]["line"] == 2
    assert "stack trace" in search["matches"][0]["text"]
    download = await invoke(logs, "download_file", path="app.log")
    assert Path(download["local_path"]).read_bytes() == before
    assert download["sha256"] == hashlib.sha256(before).hexdigest()
    assert (remote / "logs" / "app.log").read_bytes() == before
    assert sorted(p.name for p in (remote / "logs").iterdir()) == ["app.log", "nested"]


async def test_path_escape_and_directory_read(service):
    logs, _, _ = service
    assert "error" in await invoke(logs, "read_log", path="../outside.txt")
    assert "error" in await invoke(logs, "read_log", path="nested")
    assert "error" in await logs.call("read_log", environment="unknown", root="app", path="app.log")


async def test_exact_download_boundary(service):
    logs, remote, _ = service
    with (remote / "logs" / "big.log").open("wb") as f:
        f.truncate(DOWNLOAD_LIMIT)
    result = await invoke(logs, "download_file", path="big.log")
    assert "strictly below" in result["error"]
    assert not logs.destination.exists()


async def test_size_and_search_limits(service, monkeypatch):
    logs, _, _ = service
    assert "error" in await invoke(logs, "read_log", path="app.log", max_bytes=256001)
    monkeypatch.setattr(core, "SCAN_LIMIT", 8)
    search = await invoke(logs, "search_logs", paths=["app.log"], text="absent")
    assert search["truncated"] and search["files"][0]["bytes_scanned"] == 8
    assert "error" in await invoke(logs, "search_logs", paths=["app.log"], text="")


async def test_host_key_mismatch_fails_closed(service):
    logs, _, _ = service
    Path(logs.environments["test"]["known_hosts"]).write_text("")
    assert "error" in await invoke(logs, "read_log", path="app.log")


async def test_mcp_registration_and_readonly_annotations(service):
    _, _, config_path = service
    mcp = build(str(config_path))
    tools = await mcp.list_tools()
    assert {t.name for t in tools} == {"list_servers", "list_directory", "find_files", "read_log", "search_logs", "download_file"}
    assert all(t.annotations.readOnlyHint for t in tools if t.name != "download_file")
    assert next(t for t in tools if t.name == "download_file").annotations.readOnlyHint is False


@pytest.mark.skipif(os.name != "nt", reason="Windows DPAPI only")
def test_dpapi_roundtrip():
    secret = "test-password-\u20ac"
    cipher = protect(secret)
    assert secret not in cipher
    assert unprotect(cipher) == secret


async def test_symlink_rejected(service):
    logs, remote, _ = service
    link = remote / "logs" / "escape.log"
    try:
        link.symlink_to(remote / "outside.txt")
    except OSError:
        pytest.skip("Windows symlink privilege unavailable; exercised with mock below")
    assert "error" in await invoke(logs, "read_log", path="escape.log")


async def test_symlink_validation_without_windows_privilege(service):
    logs, _, _ = service
    class Fake:
        async def lstat(self, _):
            return asyncssh.SFTPAttrs(permissions=stat.S_IFLNK | 0o777)
    with pytest.raises(ValueError, match="Symlinks"):
        await logs.safe_path(Fake(), "/logs", "escape.log")


async def test_operation_timeout(service, monkeypatch):
    logs, _, _ = service
    @asynccontextmanager
    async def stalled(*_):
        await asyncio.sleep(10)
        yield None, None
    monkeypatch.setattr(logs, "session", stalled)
    monkeypatch.setattr(core, "OPERATION_TIMEOUT", 0.02)
    result = await invoke(logs, "read_log", path="app.log")
    assert result["retryable"] and "timed out" in result["error"]


async def test_download_growth_and_cancel_cleanup(service):
    logs, _, _ = service
    attrs = asyncssh.SFTPAttrs(size=1, permissions=stat.S_IFREG | 0o444, mtime=1)
    class Handle:
        async def __aenter__(self):
            return self
        async def __aexit__(self, *_):
            pass
        async def stat(self):
            return attrs
        async def read(self, _):
            return b"x" * 4
    class SFTP:
        async def lstat(self, _):
            return attrs
        async def stat(self, _):
            return attrs
        async def realpath(self, value):
            return value
        def open(self, _, mode):
            assert mode == "rb"
            return Handle()
    # Small synthetic boundary exercises growth without a 100 MB allocation.
    original = core.DOWNLOAD_LIMIT
    core.DOWNLOAD_LIMIT = 8
    try:
        with pytest.raises(ValueError, match="boundary"):
            await logs._download_file(SFTP(), "/logs", "test", "app", "app.log")
        assert not list(logs.destination.iterdir())
    finally:
        core.DOWNLOAD_LIMIT = original
    async def cancel_read(self, _):
        raise asyncio.CancelledError
    Handle.read = cancel_read
    with pytest.raises(asyncio.CancelledError):
        await logs._download_file(SFTP(), "/logs", "test", "app", "app.log")
    assert not list(logs.destination.iterdir())


@pytest.mark.skipif(os.name != "nt", reason="Child process needs real DPAPI config")
async def test_stdio_mcp_end_to_end(service):
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    _, _, config = service
    source = Path(__file__).resolve().parents[1] / "src"
    params = StdioServerParameters(command=sys.executable,
        args=["-m", "remote_logs.server", "--config", str(config)],
        env={**os.environ, "PYTHONPATH": str(source)})
    async with stdio_client(params) as (read, write):
        async with ClientSession(read, write) as client:
            await client.initialize()
            tools = await client.list_tools()
            assert len(tools.tools) == 6
            result = await client.call_tool("list_servers", {})
            assert not result.isError
            result = await client.call_tool("read_log", {"environment": "test", "root": "app", "path": "app.log"})
            assert not result.isError
            assert "ABC123" in str(result.content)

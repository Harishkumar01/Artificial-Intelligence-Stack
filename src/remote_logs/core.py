import asyncio
import fnmatch
import hashlib
import json
import os
import posixpath
import re
import stat
import uuid
from contextlib import asynccontextmanager
from pathlib import Path, PurePosixPath

import asyncssh

from .security import unprotect

DOWNLOAD_LIMIT = 100_000_000  # Strictly less than 100 decimal MB
SCAN_LIMIT = 8_000_000
READ_LIMIT = 256_000
ENTRY_LIMIT = 2000
TEXT_LIMIT = 64_000
OPERATION_TIMEOUT = 30
DOWNLOAD_TIMEOUT = 60


def relative(path: str) -> str:
    if not isinstance(path, str) or len(path) > 4096 or "\\" in path or "\x00" in path:
        raise ValueError("Use a relative POSIX path.")
    p = PurePosixPath(path)
    if p.is_absolute() or ".." in p.parts:
        raise ValueError("Absolute paths and parent traversal are forbidden.")
    return str(p)


def bounded(value: int, low: int, high: int) -> int:
    if not low <= value <= high:
        raise ValueError(f"Value must be between {low} and {high}.")
    return value


class Logs:
    def __init__(self, config_path: str):
        self.config_path = Path(config_path).resolve()
        self.config = json.loads(self.config_path.read_text(encoding="utf-8-sig"))
        self.environments = self.config["environments"]
        for env in self.environments.values():
            if not env.get("host") or not env.get("username") or not env.get("password_dpapi"):
                raise ValueError("Each environment needs host, username, and password_dpapi.")
            bounded(env.get("port", 22), 1, 65535)
            if not env.get("roots"):
                raise ValueError("Configure at least one approved root.")
            for root in env["roots"].values():
                if not root.startswith("/") or root == "/" or ".." in PurePosixPath(root).parts:
                    raise ValueError("Approved roots must be absolute, non-root POSIX paths.")
            if not env.get("known_hosts"):
                raise ValueError("A verified known_hosts file is mandatory.")
        self.destination = self.local_path(self.config["download_directory"])
        self.gate = asyncio.Semaphore(2)

    def local_path(self, value):
        p = Path(value).expanduser()
        return (self.config_path.parent / p).resolve() if not p.is_absolute() else p.resolve()

    def list_servers(self):
        return {"environments": [{"environment": name, "host": env["host"],
                 "roots": env["roots"]} for name, env in self.environments.items()],
                "download_limit_bytes_exclusive": DOWNLOAD_LIMIT,
                "prerequisite": "Connect the VPN before remote operations."}

    @asynccontextmanager
    async def session(self, environment, root):
        env = self.environments.get(environment)
        if env is None or root not in env["roots"]:
            raise ValueError("Unknown environment or approved root alias.")
        async with asyncssh.connect(env["host"], port=env.get("port", 22),
                username=env["username"], password=unprotect(env["password_dpapi"]),
                known_hosts=str(self.local_path(env["known_hosts"])),
                config=None, client_keys=[], agent_path=None,
                preferred_auth="password", connect_timeout=10, login_timeout=10) as conn:
            async with conn.start_sftp_client() as sftp:
                base = await sftp.realpath(env["roots"][root])
                yield sftp, base

    async def safe_path(self, sftp, base, path):
        path = relative(path)
        target = base
        # Reject symlinks below the administrator-configured canonical root.
        for part in PurePosixPath(path).parts:
            target = posixpath.join(target, part)
            attrs = await sftp.lstat(target)
            if attrs.permissions is None or stat.S_ISLNK(attrs.permissions):
                raise ValueError("Symlinks or unknown file types are not accessible.")
        resolved = await sftp.realpath(target)
        if resolved != base and not resolved.startswith(base.rstrip("/") + "/"):
            raise ValueError("Path escapes the approved root.")
        return resolved

    async def regular(self, sftp, base, path):
        target = await self.safe_path(sftp, base, path)
        attrs = await sftp.stat(target)
        if attrs.permissions is None or not stat.S_ISREG(attrs.permissions):
            raise ValueError("Only regular files can be read or downloaded.")
        return target, attrs

    async def call(self, operation, **args):
        try:
            async with asyncio.timeout(DOWNLOAD_TIMEOUT if operation == "download_file" else OPERATION_TIMEOUT):
                async with self.gate:
                    async with self.session(args["environment"], args["root"]) as (sftp, base):
                        result = await getattr(self, "_" + operation)(sftp, base, **args)
                        return {"environment": args["environment"], "root": args["root"],
                                "content_is_untrusted_log_data": True, **result}
        except TimeoutError:
            return {"error": "Operation timed out. Check VPN or narrow the request.", "retryable": True}
        except ValueError as exc:
            return {"error": str(exc)}
        except (asyncssh.Error, OSError, RuntimeError):
            # Never return exception strings which may contain credential/config details.
            return {"error": "SFTP/local access failed. Check VPN, credentials, host key, permissions and configuration."}

    async def entries(self, sftp, target):
        values = []
        async for item in sftp.scandir(target):
            if item.filename in (".", ".."):
                continue
            if "/" in item.filename or "\\" in item.filename or "\x00" in item.filename:
                continue
            values.append(item)
            if len(values) >= ENTRY_LIMIT:
                return values, True
        return values, False

    @staticmethod
    def metadata(item, path):
        mode = item.attrs.permissions or 0
        return {"path": path, "type": "directory" if stat.S_ISDIR(mode) else
                "file" if stat.S_ISREG(mode) else "blocked",
                "size_bytes": item.attrs.size, "modified_unix": item.attrs.mtime}

    async def _list_directory(self, sftp, base, environment, root, path=".", offset=0, limit=100):
        bounded(offset, 0, ENTRY_LIMIT)
        bounded(limit, 1, 200)
        target = await self.safe_path(sftp, base, path)
        entries, capped = await self.entries(sftp, target)
        entries.sort(key=lambda x: x.filename)
        page = entries[offset:offset + limit]
        return {"path": path, "entries": [self.metadata(x, posixpath.join(path, x.filename)) for x in page],
                "next_offset": offset + limit if offset + limit < len(entries) else None,
                "truncated": capped, "pagination_note": "Offsets are best-effort if directory contents change; capped listings cannot page past 2000 entries."}

    async def _find_files(self, sftp, base, environment, root, path=".", pattern="*.log*", max_depth=4, limit=100):
        bounded(max_depth, 0, 8)
        bounded(limit, 1, 200)
        queue = [(relative(path), 0)]
        found, visited, truncated = [], 0, False
        while queue:
            directory, depth = queue.pop()
            target = await self.safe_path(sftp, base, directory)
            entries, capped = await self.entries(sftp, target)
            truncated |= capped
            for item in entries:
                visited += 1
                if visited > ENTRY_LIMIT:
                    return {"files": found, "truncated": True}
                rel = posixpath.join(directory, item.filename)
                mode = item.attrs.permissions or 0
                if stat.S_ISDIR(mode) and depth < max_depth:
                    queue.append((rel, depth + 1))
                elif stat.S_ISDIR(mode):
                    truncated = True
                elif stat.S_ISREG(mode) and fnmatch.fnmatchcase(item.filename, pattern):
                    found.append(self.metadata(item, rel))
                    if len(found) >= limit:
                        return {"files": found, "truncated": True}
        return {"files": found, "truncated": truncated, "entries_examined": visited}

    async def _read_log(self, sftp, base, environment, root, path, offset=0, max_bytes=64000, tail=False):
        bounded(offset, 0, 2**63 - 1)
        bounded(max_bytes, 1, READ_LIMIT)
        if path.lower().endswith((".gz", ".zip", ".bz2", ".xz")):
            raise ValueError("Compressed logs are download-only in v1.")
        target, before = await self.regular(sftp, base, path)
        start = max(0, (before.size or 0) - max_bytes) if tail else offset
        async with sftp.open(target, "rb") as handle:
            await handle.seek(start)
            data = await handle.read(min(max_bytes, max(0, (before.size or 0) - start)))
            after = await handle.stat()
        return {"path": path, "byte_offset": start, "bytes_read": len(data),
                "next_offset": start + len(data), "text": data.decode("utf-8", errors="replace"),
                "truncated": start > 0 or start + len(data) < (before.size or 0),
                "changed_during_read": (before.size, before.mtime) != (after.size, after.mtime),
                "note": "UTF-8 replacement decoding; byte windows may split lines or characters."}

    async def _search_logs(self, sftp, base, environment, root, paths, text, case_sensitive=True, context_lines=2, limit=50):
        if not 1 <= len(paths) <= 20 or not 1 <= len(text) <= 1024:
            raise ValueError("Supply 1–20 paths and 1–1024 characters of literal search text.")
        bounded(context_lines, 0, 5)
        bounded(limit, 1, 100)
        remaining, output_size, matches, files = SCAN_LIMIT, 0, [], []
        needle = text if case_sensitive else text.casefold()
        for path in paths:
            target, before = await self.regular(sftp, base, path)
            if path.lower().endswith((".gz", ".zip", ".bz2", ".xz")):
                raise ValueError("Compressed logs are download-only in v1.")
            take = min(before.size or 0, remaining)
            async with sftp.open(target, "rb") as handle:
                data = await handle.read(take)
                after = await handle.stat()
            remaining -= len(data)
            partial = len(data) < (before.size or 0)
            lines = data.decode("utf-8", errors="replace").splitlines()
            files.append({"path": path, "bytes_scanned": len(data), "truncated": partial,
                          "changed_during_read": (before.size, before.mtime) != (after.size, after.mtime)})
            for i, line in enumerate(lines):
                if needle in (line if case_sensitive else line.casefold()):
                    snippet = "\n".join(lines[max(0, i-context_lines):i+context_lines+1])
                    # Preserve bounded snippets even for logs with pathological line lengths.
                    snippet = snippet[:min(8000, TEXT_LIMIT-output_size)]
                    output_size += len(snippet)
                    matches.append({"path": path, "line": i+1,
                                    "context_start_line": max(1, i-context_lines+1), "text": snippet,
                                    "snippet_may_be_truncated": len(snippet) >= 8000 or output_size >= TEXT_LIMIT})
                    if len(matches) >= limit or output_size >= TEXT_LIMIT:
                        return {"matches": matches, "files": files, "truncated": True}
            if remaining <= 0:
                return {"matches": matches, "files": files, "truncated": True}
        return {"matches": matches, "files": files, "truncated": any(f["truncated"] for f in files)}

    async def _download_file(self, sftp, base, environment, root, path):
        target, before = await self.regular(sftp, base, path)
        if before.size is None or before.size >= DOWNLOAD_LIMIT:
            raise ValueError("Download rejected: file must be strictly below 100,000,000 bytes.")
        self.destination.mkdir(parents=True, exist_ok=True)
        # Generated names prevent remote paths from controlling local filesystem paths.
        token = uuid.uuid4().hex
        temp = self.destination / (token + ".partial")
        basename = re.sub(r"[^A-Za-z0-9._-]", "_", posixpath.basename(path))[-100:] or "log"
        final = self.destination / (token + "-" + basename)
        total, digest = 0, hashlib.sha256()
        try:
            async with sftp.open(target, "rb") as remote:
                opened = await remote.stat()
                if opened.permissions is None or not stat.S_ISREG(opened.permissions):
                    raise ValueError("Download rejected: opened object is not a regular file.")
                if opened.size is None or opened.size >= DOWNLOAD_LIMIT:
                    raise ValueError("Download rejected: file size changed or exceeds limit.")
                with temp.open("xb") as local:
                    while True:
                        chunk = await remote.read(min(262144, DOWNLOAD_LIMIT-total))
                        if not chunk:
                            break
                        total += len(chunk)
                        if total >= DOWNLOAD_LIMIT:
                            raise ValueError("Download stopped: file reached the 100 MB boundary.")
                        local.write(chunk)
                        digest.update(chunk)
                after = await remote.stat()
            if (before.size, before.mtime) != (after.size, after.mtime) or total != before.size:
                raise ValueError("File changed during download; partial copy discarded. Retry a rotated log.")
            os.rename(temp, final)
            return {"path": path, "local_path": str(final), "size_bytes": total,
                    "sha256": digest.hexdigest(), "changed_during_download": False,
                    "note": "Metadata checks detect common changes, not an atomic server snapshot."}
        finally:
            temp.unlink(missing_ok=True)

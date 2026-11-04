"""Operator-only interactive config editor; deliberately not exposed via MCP."""
import argparse
import getpass
import json
import os
from pathlib import Path
from .security import protect


def main():
    parser = argparse.ArgumentParser(description="Configure an SFTP environment with Windows DPAPI password encryption.")
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    if os.name != "nt":
        parser.error("Configuration with DPAPI requires Windows.")
    target = Path(args.config).resolve()
    data = json.loads(target.read_text(encoding="utf-8-sig")) if target.exists() else {
        "download_directory": "downloads", "environments": {}}
    alias = input("Environment alias (e.g. uat): ").strip()
    if not alias:
        parser.error("An environment alias is required.")
    host = input("Server IP or DNS name: ").strip()
    port = int(input("SFTP port [22]: ").strip() or "22")
    username = input("Username: ").strip()
    known_hosts = input("Verified OpenSSH known_hosts file path [known_hosts]: ").strip() or "known_hosts"
    roots = {}
    print("Add approved absolute log directories; leave the alias blank when finished.")
    while True:
        name = input("Root alias (e.g. application): ").strip()
        if not name:
            break
        root = input("Absolute remote directory: ").strip()
        if not root.startswith("/") or root == "/" or ".." in root.split("/"):
            parser.error("Use an absolute log directory below /, without parent traversal.")
        roots[name] = root
    if not host or not username or not known_hosts or not roots or not 1 <= port <= 65535:
        parser.error("Host, username, verified known_hosts, valid port, and approved roots are required.")
    password = getpass.getpass("SFTP password (hidden): ")
    if not password:
        parser.error("Password must not be empty.")
    protected = protect(password)
    del password
    data["environments"][alias] = {"host": host, "port": port, "username": username,
        "password_dpapi": protected, "known_hosts": known_hosts, "roots": roots}
    target.parent.mkdir(parents=True, exist_ok=True)
    if target.is_symlink():
        parser.error("Config must not be a symlink.")
    temp = target.with_name(target.name + ".tmp")
    try:
        with temp.open("x", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
            handle.write("\n")
        os.replace(temp, target)
    finally:
        temp.unlink(missing_ok=True)
    print(f"Saved encrypted credentials and environment to {target}")


if __name__ == "__main__":
    main()

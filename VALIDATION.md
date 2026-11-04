# Verification — 4 November 2026

Environment: Windows, Python 3.12.14, MCP SDK 1.30.0, AsyncSSH 2.24.1.

- Automated suite: **16 passed, 1 skipped**.
- Real loopback SSH/SFTP server: password login, pinned host key, directory navigation, recursive filename search, byte reads/tail, literal content search, file download and SHA-256 verification.
- A real MCP stdio child process was initialized; tool discovery returned exactly six tools and a remote log was read through MCP end to end, using real DPAPI-protected test credentials.
- Remote file opens were checked at the SFTP server for absence of write/create/append/truncate flags.
- Absolute/parent paths, directory reads, incorrect host keys and unknown environments were rejected.
- The exact 100,000,000-byte boundary was rejected using a sparse test file without downloading it. A synthetic smaller boundary tested growth interruption and removal of partial files. Cancellation cleanup and operation timeouts were checked.
- Windows DPAPI encryption/decryption round-trip passed. Test credentials are synthetic and not real server credentials.
- Windows denied filesystem symlink creation, so that integration test was skipped. A separate mocked symlink validation test passed.
- Python source compilation and dependency consistency checks passed.

Not yet verified against your Oracle Linux server, VPN, actual username/password, approved directories, or server host key: none have been supplied. No production connection was attempted. No global MCP host configuration has been modified.

Read-only access is enforced by the operations this MCP exposes. Use a read-only SFTP account for independent server enforcement. See README.md for SFTP path-race and live-file consistency limitations.

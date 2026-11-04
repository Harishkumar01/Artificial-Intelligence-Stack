"""Export one host's already-trusted PuTTY cached public keys to OpenSSH known_hosts.

No network access, passwords, private keys, or registry writes.
Run using the same Windows account as PuTTY.
"""
import argparse
import base64
import struct
from pathlib import Path

import asyncssh
from cryptography.hazmat.primitives.asymmetric import ec


def field(value):
    return struct.pack(">I", len(value)) + value


def mpint(value):
    if value <= 0:
        raise ValueError("Invalid positive public-key integer")
    data = value.to_bytes((value.bit_length() + 7) // 8, "big")
    return field(b"\0" + data if data[0] & 128 else data)


def convert(kind, value):
    parts = [s.strip() for s in value.split(",")]
    if kind == "rsa2" and len(parts) == 2:
        algorithm = "ssh-rsa"
        exponent, modulus = [int(s, 16) for s in parts]
        blob = field(algorithm.encode()) + mpint(exponent) + mpint(modulus)
    elif kind in ("ssh-ed25519", "ed25519") and len(parts) == 2:
        algorithm = "ssh-ed25519"
        x, y = [int(s, 16) for s in parts]
        prime = 2**255 - 19
        d = -121665 * pow(121666, -1, prime) % prime
        if not (0 <= x < prime and 0 <= y < prime):
            raise ValueError("Invalid Ed25519 coordinates")
        if (-x*x + y*y - 1 - d*x*x*y*y) % prime:
            raise ValueError("Invalid Ed25519 curve point")
        compressed = (y | ((x & 1) << 255)).to_bytes(32, "little")
        blob = field(algorithm.encode()) + field(compressed)
    elif kind.startswith("ecdsa-sha2-") and len(parts) == 3:
        algorithm = kind
        curve, x, y = parts
        curves = {"nistp256": ec.SECP256R1, "nistp384": ec.SECP384R1, "nistp521": ec.SECP521R1}
        if curve not in curves or algorithm != "ecdsa-sha2-" + curve:
            raise ValueError("Unsupported ECDSA curve")
        curve_obj = curves[curve]()
        x, y = int(x, 16), int(y, 16)
        ec.EllipticCurvePublicNumbers(x, y, curve_obj).public_key()  # Validate point.
        width = (curve_obj.key_size + 7) // 8
        point = b"\x04" + x.to_bytes(width, "big") + y.to_bytes(width, "big")
        blob = field(algorithm.encode()) + field(curve.encode()) + field(point)
    else:
        raise ValueError("Unsupported PuTTY host-key format: " + kind)
    line = algorithm + " " + base64.b64encode(blob).decode("ascii")
    key = asyncssh.import_public_key(line)
    return line, key.get_fingerprint("sha256")


def main():
    import winreg
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--host", required=True, help="Exact hostname/IP used in PuTTY")
    parser.add_argument("--port", type=int, default=22)
    parser.add_argument("--output", required=True, help="New local known_hosts filename; existing files are never overwritten")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535 or any(c.isspace() or c in ",*?![]\\/" for c in args.host):
        parser.error("Supply a literal hostname/IP and valid port")
    suffix = f"@{args.port}:{args.host}"
    token = args.host if args.port == 22 else f"[{args.host}]:{args.port}"
    lines, fingerprints = [], []
    try:
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, r"Software\SimonTatham\PuTTY\SshHostKeys") as registry:
            for i in range(winreg.QueryInfoKey(registry)[1]):
                name, value, value_type = winreg.EnumValue(registry, i)
                if name.endswith(suffix) and value_type == winreg.REG_SZ:
                    kind = name[:-len(suffix)]
                    if kind not in ("rsa2", "ssh-ed25519", "ed25519") and not kind.startswith("ecdsa-sha2-"):
                        print(f"Skipped unsupported legacy key type: {kind}")
                        continue
                    public, fingerprint = convert(kind, value)
                    lines.append(token + " " + public + "\n")
                    fingerprints.append((kind, fingerprint))
    except FileNotFoundError:
        parser.error("PuTTY host-key cache is absent under this Windows account")
    if not lines:
        parser.error("No supported cached key matches that exact host and port; use the same hostname/IP as PuTTY")
    target = Path(args.output).resolve()
    if not target.parent.is_dir():
        parser.error("Output parent directory does not exist")
    try:
        with target.open("x", encoding="ascii", newline="\n") as handle:
            handle.writelines(lines)
    except FileExistsError:
        parser.error("Output already exists; choose a new filename to avoid overwriting trusted keys")
    print(f"Exported {len(lines)} cached public host key(s) to {target}")
    for kind, fingerprint in fingerprints:
        print(f"{kind}: {fingerprint}")


if __name__ == "__main__":
    main()

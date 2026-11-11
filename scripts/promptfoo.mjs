// Run the bundle's locked Promptfoo installation; keep its viewer on this computer.
import fs from 'node:fs';
import http from 'node:http';
import net from 'node:net';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const packageDir = path.join(root, 'node_modules', 'promptfoo');
const args = process.argv.slice(2);
if (!['view', 'eval', 'validate', '--version', '--help'].includes(args[0]) ||
    args.some(arg => /^(?:--view|--watch)(?:=|$)/.test(arg))) {
  console.error('Use this lab launcher for eval, validate, --version, or view. Start the viewer with its separate view command.');
  process.exit(1);
}
try {
  const installed = JSON.parse(fs.readFileSync(path.join(packageDir, 'package.json'), 'utf8'));
  if (installed.version !== '0.121.18') throw new Error('Unexpected Promptfoo version');
} catch {
  console.error('Run npm ci --ignore-scripts --registry=https://registry.npmjs.org from the bundle root to install the locked Promptfoo dependencies.');
  process.exit(1);
}

// Explicit paths work when a Python evaluator starts this process from its lab folder.
process.chdir(root);
process.env.PROMPTFOO_CONFIG_DIR = path.join(root, '.promptfoo');
process.env.PROMPTFOO_DISABLE_TELEMETRY = '1';
process.env.PROMPTFOO_DISABLE_UPDATE = '1';

// Gate requests before Express or Socket.IO sees them. Loopback binding alone
// does not prevent an unrelated website from sending requests to a local service.
const originalEmit = http.Server.prototype.emit;
http.Server.prototype.emit = function (event, ...eventArgs) {
  if (event === 'request' || event === 'upgrade') {
    const [request, responseOrSocket] = eventArgs;
    const port = request.socket.localPort;
    const authorities = [`localhost:${port}`, `127.0.0.1:${port}`];
    const urls = authorities.map(host => new URL(`http://${host}`));
    const hosts = new Set([...authorities, ...urls.map(url => url.host)]);
    const origins = new Set(urls.map(url => url.origin));
    const origin = request.headers.origin;
    const allowed = hosts.has(request.headers.host?.toLowerCase()) &&
      (origin === undefined || origins.has(origin)) &&
      request.headers['sec-fetch-site'] !== 'cross-site';
    if (!allowed) {
      if (event === 'request') {
        responseOrSocket.writeHead(403, { 'Content-Type': 'text/plain', 'Connection': 'close' });
        responseOrSocket.end('Only same-site requests to the local lab viewer are allowed.\n');
      } else {
        responseOrSocket.end('HTTP/1.1 403 Forbidden\r\nConnection: close\r\nContent-Length: 0\r\n\r\n');
      }
      return true;
    }
  }
  return originalEmit.call(this, event, ...eventArgs);
};
const originalListen = net.Server.prototype.listen;
net.Server.prototype.listen = function (...listenArgs) {
  // The pinned server uses listen(port, callback). Fail closed if that contract changes.
  if (listenArgs.length !== 2 || typeof listenArgs[1] !== 'function') {
    throw new Error('Unexpected viewer listener contract; refusing to start.');
  }
  return originalListen.call(this, listenArgs[0], '127.0.0.1', listenArgs[1]);
};

if (args[0] === 'view') {
  if (args.length !== 1) {
    console.error('Use: node scripts/promptfoo.mjs view (optional port: API_PORT environment variable).');
    process.exit(1);
  }
  const port = process.env.API_PORT ?? '15500';
  if (!/^\d+$/.test(port) || Number(port) < 1 || Number(port) > 65535) {
    console.error('API_PORT must be an integer from 1 to 65535.');
    process.exit(1);
  }
  process.env.API_PORT = String(Number(port));

  await import(pathToFileURL(path.join(packageDir, 'dist', 'src', 'server', 'index.js')));
} else {
  // CLI evaluation/configuration commands remain the pinned upstream implementation.
  const entry = path.join(packageDir, 'dist', 'src', 'entrypoint.js');
  process.argv = [process.execPath, entry, ...args];
  await import(pathToFileURL(entry));
}

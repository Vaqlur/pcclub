import { spawn } from 'node:child_process';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const rootDir = dirname(fileURLToPath(import.meta.url));
const mobileDir = resolve(rootDir, 'mobile');
const port = process.env.PORT || '3000';

const child = spawn(
  'npx',
  ['expo', 'start', '--web', '--port', String(port)],
  {
    cwd: mobileDir,
    stdio: ['pipe', 'inherit', 'inherit'],
    env: {
      ...process.env,
      PORT: String(port),
      BROWSER: 'none',
    },
  },
);

child.on('exit', (code, signal) => {
  if (signal) {
    process.kill(process.pid, signal);
  } else {
    process.exit(code ?? 0);
  }
});

for (const sig of ['SIGINT', 'SIGTERM']) {
  process.on(sig, () => {
    child.kill(sig);
  });
}

import { createReadStream } from 'node:fs';
import { open, stat } from 'node:fs/promises';
import { createInterface } from 'node:readline';
import { processLine } from './application.js';

async function main(): Promise<void> {
  const [input, output] = process.argv.slice(2);
  if (!input || !output || process.argv.length !== 4) {
    throw new Error('Usage: worker.sh INPUT_JSONL OUTPUT_JSONL');
  }
  const inputInfo = await stat(input);
  const outputInfo = await stat(output).catch((error: NodeJS.ErrnoException) => {
    if (error.code === 'ENOENT') return undefined;
    throw error;
  });
  if (outputInfo && inputInfo.dev === outputInfo.dev && inputInfo.ino === outputInfo.ino) {
    throw new Error('Input and output must be different files');
  }
  const destination = await open(output, 'w');
  const source = createReadStream(input, { encoding: 'utf8' });
  const lines = createInterface({ input: source, crlfDelay: Infinity });
  let pending = '';
  try {
    for await (const line of lines) {
      if (line.trim().length === 0) continue;
      pending += JSON.stringify(processLine(line)) + '\n';
      if (pending.length >= 65536) {
        await destination.writeFile(pending, 'utf8');
        pending = '';
      }
    }
    if (pending) await destination.writeFile(pending, 'utf8');
  } finally {
    lines.close();
    source.destroy();
    await destination.close();
  }
}

main().catch((error: unknown) => {
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
});

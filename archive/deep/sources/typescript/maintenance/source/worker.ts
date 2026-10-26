import { closeSync, fstatSync, openSync, readSync, statSync, writeSync } from 'node:fs';
import { StringDecoder } from 'node:string_decoder';
import { processLine } from './application.js';

function main(): void {
  const [input, output] = process.argv.slice(2);
  if (!input || !output || process.argv.length !== 4) {
    throw new Error('Usage: worker.sh INPUT_JSONL OUTPUT_JSONL');
  }
  const source = openSync(input, 'r');
  let destination: number | undefined;
  try {
    const inputInfo = fstatSync(source);
    let outputInfo;
    try { outputInfo = statSync(output); }
    catch (error) { if ((error as NodeJS.ErrnoException).code !== 'ENOENT') throw error; }
    if (outputInfo && inputInfo.dev === outputInfo.dev && inputInfo.ino === outputInfo.ino) {
      throw new Error('Input and output must be different files');
    }
    destination = openSync(output, 'w');
    const buffer = Buffer.allocUnsafe(64 * 1024);
    const decoder = new StringDecoder('utf8');
    let carry = '', pending = '';
    function flush(): void {
      const bytes = Buffer.from(pending, 'utf8');
      let offset = 0;
      while (offset < bytes.length) offset += writeSync(destination!, bytes, offset, bytes.length - offset);
      pending = '';
    }
    function line(value: string): void {
      if (value.trim().length === 0) return;
      pending += JSON.stringify(processLine(value)) + '\n';
      if (pending.length >= 65536) flush();
    }
    for (;;) {
      const size = readSync(source, buffer, 0, buffer.length, null);
      if (size === 0) break;
      const chunk = carry + decoder.write(buffer.subarray(0, size));
      let start = 0, end: number;
      while ((end = chunk.indexOf('\n', start)) !== -1) {
        line(chunk.slice(start, end));
        start = end + 1;
      }
      carry = chunk.slice(start);
    }
    carry += decoder.end();
    if (carry) line(carry);
    if (pending) flush();
  } finally {
    closeSync(source);
    if (destination !== undefined) closeSync(destination);
  }
}

try { main(); }
catch (error: unknown) {
  console.error(error instanceof Error ? error.message : String(error));
  process.exitCode = 1;
}

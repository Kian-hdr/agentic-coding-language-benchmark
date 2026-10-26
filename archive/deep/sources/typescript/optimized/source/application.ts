export interface InvoiceEvent {
  id: string; customer: string; amount_cents: number; status: string;
}
export interface AccessEvent {
  ts_ms: number; route: string; status: number; duration_us: number; bytes: number;
}
export type Request =
  | { op: 'invoice'; events: InvoiceEvent[] }
  | { op: 'access_log'; start_ms: number; end_ms: number; events: AccessEvent[] }
  | { op: 'telemetry'; samples: number[]; window: number; threshold: number };

// JavaScript trim also removes Unicode whitespace, which this protocol preserves.
function asciiWhitespace(c: number): boolean { return c === 32 || (c >= 9 && c <= 13); }
function trimASCII(s: string): string {
  let start = 0, end = s.length;
  while (start < end && asciiWhitespace(s.charCodeAt(start))) start++;
  while (end > start && asciiWhitespace(s.charCodeAt(end - 1))) end--;
  return start === 0 && end === s.length ? s : s.slice(start, end);
}
const lexical = (a: string, b: string): number => a < b ? -1 : a > b ? 1 : 0;

export function invoice(events: InvoiceEvent[]) {
  const seen = new Set<string>();
  const customers = new Map<string, {
    customer: string; gross_cents: number; refund_cents: number; net_cents: number; count: number;
  }>();
  let accepted = 0, duplicates = 0, ignored = 0, rejected = 0;
  let gross_cents = 0, refund_cents = 0;
  for (const event of events) {
    if (seen.has(event.id)) { duplicates++; continue; }
    seen.add(event.id);
    const customer = trimASCII(event.customer);
    const status = event.status;
    if (!customer || event.amount_cents < 0 ||
        (status !== 'paid' && status !== 'refund' && status !== 'pending' && status !== 'void')) {
      rejected++;
      continue;
    }
    if (status === 'pending' || status === 'void') { ignored++; continue; }
    accepted++;
    let row = customers.get(customer);
    if (!row) {
      row = { customer, gross_cents: 0, refund_cents: 0, net_cents: 0, count: 0 };
      customers.set(customer, row);
    }
    row.count++;
    if (status === 'paid') {
      row.gross_cents += event.amount_cents;
      gross_cents += event.amount_cents;
    } else {
      row.refund_cents += event.amount_cents;
      refund_cents += event.amount_cents;
    }
  }
  for (const row of customers.values()) row.net_cents = row.gross_cents - row.refund_cents;
  return {
    customers: [...customers.values()].sort((a, b) => lexical(a.customer, b.customer)),
    accepted, duplicates, ignored, rejected, gross_cents, refund_cents,
    net_cents: gross_cents - refund_cents
  };
}

// Three-way selection avoids sorting every duration, including repeated values.
// Limit partition work so adversarial pivot arrangements fall back to native sort.
function select(values: number[], k: number): number {
  let left = 0, right = values.length - 1, budget = values.length * 4;
  while (left < right) {
    budget -= right - left + 1;
    if (budget < 0) { values.sort((a, b) => a - b); return values[k]; }
    const a = values[left], b = values[(left + right) >>> 1], c = values[right];
    const pivot = a < b ? (b < c ? b : a < c ? c : a) : (a < c ? a : b < c ? c : b);
    let low = left, i = left, high = right;
    while (i <= high) {
      const value = values[i];
      if (value < pivot) {
        values[i] = values[low]; values[low++] = value; i++;
      } else if (value > pivot) {
        values[i] = values[high]; values[high--] = value;
      } else i++;
    }
    if (k < low) right = low - 1;
    else if (k > high) left = high + 1;
    else return pivot;
  }
  return values[left];
}

export function accessLog(start: number, end: number, events: AccessEvent[]) {
  const groups = new Map<string, {
    route: string; count: number; errors: number; total_bytes: number; max_us: number; durations: number[];
  }>();
  let total_count = 0, total_errors = 0, total_bytes = 0;
  for (const event of events) {
    if (event.ts_ms < start || event.ts_ms >= end) continue;
    const route = trimASCII(event.route);
    let row = groups.get(route);
    if (!row) {
      row = { route, count: 0, errors: 0, total_bytes: 0, max_us: 0, durations: [] };
      groups.set(route, row);
    }
    const error = event.status >= 500 ? 1 : 0;
    row.count++;
    row.errors += error;
    row.total_bytes += event.bytes;
    row.max_us = Math.max(row.max_us, event.duration_us);
    row.durations.push(event.duration_us);
    total_count++;
    total_errors += error;
    total_bytes += event.bytes;
  }
  const routes = [...groups.values()].sort((a, b) => lexical(a.route, b.route)).map(row => {
    return { route: row.route, count: row.count, errors: row.errors,
      total_bytes: row.total_bytes, max_us: row.max_us,
      p95_us: select(row.durations, Math.ceil(95 * row.count / 100) - 1) };
  });
  return { routes, total_count, total_errors, total_bytes };
}

export function telemetry(samples: number[], window: number, threshold: number) {
  if (window <= 0 || window > samples.length) return { error: 'invalid_window' };
  // Exact Number integers cover the specified domain. Retry with BigInt if a
  // rolling-update transient or a weighted partial sum exceeds that domain.
  let sum = 0;
  for (let i = 0; i < window; i++) {
    sum += samples[i];
    if (!Number.isSafeInteger(sum)) return telemetryExact(samples, window, threshold);
  }
  const count = samples.length - window + 1;
  let min = Infinity, max = -Infinity, above = 0, checksum = 0;
  for (let i = 0; i < count; i++) {
    if (i > 0) {
      sum -= samples[i - 1];
      if (!Number.isSafeInteger(sum)) return telemetryExact(samples, window, threshold);
      sum += samples[i + window - 1];
      if (!Number.isSafeInteger(sum)) return telemetryExact(samples, window, threshold);
    }
    const average = Math.trunc(sum / window) || 0;
    if (average < min) min = average;
    if (average > max) max = average;
    if (average > threshold) above++;
    const weighted = (i + 1) * average;
    checksum += weighted;
    if (!Number.isSafeInteger(weighted) || !Number.isSafeInteger(checksum)) {
      return telemetryExact(samples, window, threshold);
    }
  }
  return { count, min, max, above, weighted_checksum: checksum };
}

function telemetryExact(samples: number[], window: number, threshold: number) {
  const divisor = BigInt(window), limit = BigInt(threshold);
  let sum = 0n;
  for (let i = 0; i < window; i++) sum += BigInt(samples[i]);
  let min = sum / divisor, max = min, above = 0, checksum = 0n;
  const count = samples.length - window + 1;
  for (let i = 0; i < count; i++) {
    if (i > 0) sum += BigInt(samples[i + window - 1]) - BigInt(samples[i - 1]);
    const average = sum / divisor;
    if (average < min) min = average;
    if (average > max) max = average;
    if (average > limit) above++;
    checksum += BigInt(i + 1) * average;
  }
  return { count, min: Number(min), max: Number(max), above, weighted_checksum: Number(checksum) };
}

export function processLine(line: string): unknown {
  let value: unknown;
  try { value = JSON.parse(line); }
  catch { return { error: 'invalid_json' }; }
  const request = value as Request | null;
  switch (request?.op) {
    case 'invoice': return invoice(request.events);
    case 'access_log': return accessLog(request.start_ms, request.end_ms, request.events);
    case 'telemetry': return telemetry(request.samples, request.window, request.threshold);
    default: return { error: 'unknown_op' };
  }
}

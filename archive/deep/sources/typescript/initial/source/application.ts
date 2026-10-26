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
const trimASCII = (s: string): string => s.replace(/^[ \t\n\r\v\f]+|[ \t\n\r\v\f]+$/g, '');
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
    row.net_cents = row.gross_cents - row.refund_cents;
  }
  return {
    customers: [...customers.values()].sort((a, b) => lexical(a.customer, b.customer)),
    accepted, duplicates, ignored, rejected, gross_cents, refund_cents,
    net_cents: gross_cents - refund_cents
  };
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
    row.durations.sort((a, b) => a - b);
    return { route: row.route, count: row.count, errors: row.errors,
      total_bytes: row.total_bytes, max_us: row.max_us,
      p95_us: row.durations[Math.ceil(95 * row.count / 100) - 1] };
  });
  return { routes, total_count, total_errors, total_bytes };
}

export function telemetry(samples: number[], window: number, threshold: number) {
  if (window <= 0 || window > samples.length) return { error: 'invalid_window' };
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

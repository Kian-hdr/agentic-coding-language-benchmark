package main

import (
	"bufio"
	"bytes"
	"encoding/json"
	"fmt"
	"io"
	"os"
	"slices"
	"sort"
	"strings"
)

const asciiSpace = " \t\n\r\v\f"

type failure struct {
	Error string `json:"error"`
}
type invoiceEvent struct {
	ID       string `json:"id"`
	Customer string `json:"customer"`
	Amount   int64  `json:"amount_cents"`
	Status   string `json:"status"`
}
type customerRow struct {
	Customer string `json:"customer"`
	Gross    int64  `json:"gross_cents"`
	Refund   int64  `json:"refund_cents"`
	Net      int64  `json:"net_cents"`
	Count    int64  `json:"count"`
}
type invoiceResult struct {
	Customers  []customerRow `json:"customers"`
	Accepted   int64         `json:"accepted"`
	Duplicates int64         `json:"duplicates"`
	Ignored    int64         `json:"ignored"`
	Rejected   int64         `json:"rejected"`
	Gross      int64         `json:"gross_cents"`
	Refund     int64         `json:"refund_cents"`
	Net        int64         `json:"net_cents"`
}

func invoice(events []invoiceEvent) invoiceResult {
	r := invoiceResult{Customers: make([]customerRow, 0)}
	seen := make(map[string]struct{}, len(events))
	groups := make(map[string]*customerRow)
	for _, e := range events {
		if _, ok := seen[e.ID]; ok {
			r.Duplicates++
			continue
		}
		seen[e.ID] = struct{}{}
		c := strings.Trim(e.Customer, asciiSpace)
		if c == "" || e.Amount < 0 || (e.Status != "paid" && e.Status != "refund" && e.Status != "pending" && e.Status != "void") {
			r.Rejected++
			continue
		}
		if e.Status == "pending" || e.Status == "void" {
			r.Ignored++
			continue
		}
		r.Accepted++
		row := groups[c]
		if row == nil {
			row = &customerRow{Customer: c}
			groups[c] = row
		}
		row.Count++
		if e.Status == "paid" {
			row.Gross += e.Amount
			r.Gross += e.Amount
		} else {
			row.Refund += e.Amount
			r.Refund += e.Amount
		}
	}
	for _, row := range groups {
		row.Net = row.Gross - row.Refund
		r.Customers = append(r.Customers, *row)
	}
	sort.Slice(r.Customers, func(i, j int) bool { return r.Customers[i].Customer < r.Customers[j].Customer })
	r.Net = r.Gross - r.Refund
	return r
}

type accessEvent struct {
	TS       int64  `json:"ts_ms"`
	Route    string `json:"route"`
	Status   int64  `json:"status"`
	Duration int64  `json:"duration_us"`
	Bytes    int64  `json:"bytes"`
}
type routeRow struct {
	Route      string `json:"route"`
	Count      int64  `json:"count"`
	Errors     int64  `json:"errors"`
	TotalBytes int64  `json:"total_bytes"`
	Max        int64  `json:"max_us"`
	P95        int64  `json:"p95_us"`
}
type accessResult struct {
	Routes []routeRow `json:"routes"`
	Count  int64      `json:"total_count"`
	Errors int64      `json:"total_errors"`
	Bytes  int64      `json:"total_bytes"`
}
type routeGroup struct {
	row       routeRow
	durations []int64
}

func accessLog(start, end int64, events []accessEvent) accessResult {
	r := accessResult{Routes: make([]routeRow, 0)}
	groups := make(map[string]*routeGroup)
	for _, e := range events {
		if e.TS < start || e.TS >= end {
			continue
		}
		route := strings.Trim(e.Route, asciiSpace)
		g := groups[route]
		if g == nil {
			g = &routeGroup{row: routeRow{Route: route}}
			groups[route] = g
		}
		g.row.Count++
		r.Count++
		if e.Status >= 500 {
			g.row.Errors++
			r.Errors++
		}
		g.row.TotalBytes += e.Bytes
		r.Bytes += e.Bytes
		if e.Duration > g.row.Max {
			g.row.Max = e.Duration
		}
		g.durations = append(g.durations, e.Duration)
	}
	for _, g := range groups {
		g.row.P95 = selectDuration(g.durations, len(g.durations)-len(g.durations)/20-1)
		r.Routes = append(r.Routes, g.row)
	}
	sort.Slice(r.Routes, func(i, j int) bool { return r.Routes[i].Route < r.Routes[j].Route })
	return r
}

// Three-way partitioning handles repeated durations without quadratic scans.
// Bound total partition work, falling back to the standard sort if necessary.
func selectDuration(a []int64, k int) int64 {
	budget := 2 * len(a)
	for len(a) > 24 && budget >= len(a) {
		budget -= len(a)
		x, y, z := a[0], a[len(a)/2], a[len(a)-1]
		if x > y {
			x, y = y, x
		}
		if y > z {
			y = z
		}
		if x > y {
			y = x
		}
		pivot := y
		lo, i, hi := 0, 0, len(a)
		for i < hi {
			if a[i] < pivot {
				a[lo], a[i] = a[i], a[lo]
				lo++
				i++
			} else if a[i] > pivot {
				hi--
				a[i], a[hi] = a[hi], a[i]
			} else {
				i++
			}
		}
		if k < lo {
			a = a[:lo]
		} else if k >= hi {
			a = a[hi:]
			k -= hi
		} else {
			return pivot
		}
	}
	slices.Sort(a)
	return a[k]
}

type telemetryResult struct {
	Count    int64 `json:"count"`
	Min      int64 `json:"min"`
	Max      int64 `json:"max"`
	Above    int64 `json:"above"`
	Checksum int64 `json:"weighted_checksum"`
}

func telemetry(samples []int64, window, threshold int64) any {
	if window <= 0 || window > int64(len(samples)) {
		return failure{"invalid_window"}
	}
	w := int(window)
	var sum int64
	for _, v := range samples[:w] {
		sum += v
	}
	r := telemetryResult{}
	for end := w; ; end++ {
		avg := sum / window
		if r.Count == 0 || avg < r.Min {
			r.Min = avg
		}
		if r.Count == 0 || avg > r.Max {
			r.Max = avg
		}
		r.Count++
		if avg > threshold {
			r.Above++
		}
		r.Checksum += r.Count * avg
		if end == len(samples) {
			break
		}
		sum -= samples[end-w]
		sum += samples[end]
	}
	return r
}

// The input line remains alive throughout processing, so event JSON can be
// borrowed rather than copied by json.RawMessage.
type borrowedJSON []byte

func (b *borrowedJSON) UnmarshalJSON(data []byte) error { *b = data; return nil }

type request struct {
	Op        string       `json:"op"`
	Events    borrowedJSON `json:"events"`
	Samples   []int64      `json:"samples"`
	Window    int64        `json:"window"`
	Threshold int64        `json:"threshold"`
	Start     int64        `json:"start_ms"`
	End       int64        `json:"end_ms"`
}
type processor struct {
	req      request
	invoices []invoiceEvent
	accesses []accessEvent
}

func process(line []byte) any { return new(processor).process(line) }

func (p *processor) process(line []byte) any {
	p.req = request{Samples: p.req.Samples[:0]}
	if err := json.Unmarshal(line, &p.req); err != nil {
		// Preserve dispatch semantics for unrelated, differently typed fields.
		return processLegacy(line)
	}
	switch p.req.Op {
	case "invoice":
		if len(p.req.Events) == 0 {
			return invoice(nil)
		}
		p.invoices = p.invoices[:0]
		if err := json.Unmarshal(p.req.Events, &p.invoices); err != nil {
			clear(p.invoices)
			return failure{"invalid_json"}
		}
		r := invoice(p.invoices)
		clear(p.invoices)
		return r
	case "access_log":
		if len(p.req.Events) == 0 {
			return accessLog(p.req.Start, p.req.End, nil)
		}
		p.accesses = p.accesses[:0]
		if err := json.Unmarshal(p.req.Events, &p.accesses); err != nil {
			clear(p.accesses)
			return failure{"invalid_json"}
		}
		r := accessLog(p.req.Start, p.req.End, p.accesses)
		clear(p.accesses)
		return r
	case "telemetry":
		return telemetry(p.req.Samples, p.req.Window, p.req.Threshold)
	default:
		return failure{"unknown_op"}
	}
}

func processLegacy(line []byte) any {
	var envelope struct {
		Op string `json:"op"`
	}
	if !json.Valid(line) {
		return failure{"invalid_json"}
	}
	if err := json.Unmarshal(line, &envelope); err != nil {
		return failure{"unknown_op"}
	}
	switch envelope.Op {
	case "invoice":
		var req struct {
			Events []invoiceEvent `json:"events"`
		}
		if err := json.Unmarshal(line, &req); err != nil {
			return failure{"invalid_json"}
		}
		return invoice(req.Events)
	case "access_log":
		var req struct {
			Start  int64         `json:"start_ms"`
			End    int64         `json:"end_ms"`
			Events []accessEvent `json:"events"`
		}
		if err := json.Unmarshal(line, &req); err != nil {
			return failure{"invalid_json"}
		}
		return accessLog(req.Start, req.End, req.Events)
	case "telemetry":
		var req struct {
			Samples   []int64 `json:"samples"`
			Window    int64   `json:"window"`
			Threshold int64   `json:"threshold"`
		}
		if err := json.Unmarshal(line, &req); err != nil {
			return failure{"invalid_json"}
		}
		return telemetry(req.Samples, req.Window, req.Threshold)
	default:
		return failure{"unknown_op"}
	}
}

func run(input, output string) (err error) {
	in, err := os.Open(input)
	if err != nil {
		return err
	}
	defer in.Close()
	// Check identity before truncating, including hard links and symlinks.
	source, err := in.Stat()
	if err != nil {
		return err
	}
	if target, e := os.Stat(output); e == nil && os.SameFile(source, target) {
		return fmt.Errorf("input and output must be different files")
	}
	out, err := os.Create(output)
	if err != nil {
		return err
	}
	defer func() {
		if e := out.Close(); err == nil {
			err = e
		}
	}()
	reader := bufio.NewReaderSize(in, 64*1024)
	writer := bufio.NewWriterSize(out, 64*1024)
	encoder := json.NewEncoder(writer)
	p := processor{}
	var joined []byte
	for {
		line, e := reader.ReadSlice('\n')
		if e == bufio.ErrBufferFull {
			joined = append(joined, line...)
			continue
		}
		if e != nil && e != io.EOF {
			return e
		}
		if len(joined) != 0 {
			joined = append(joined, line...)
			line = joined
		}
		if len(bytes.Trim(line, asciiSpace)) != 0 {
			if err := encoder.Encode(p.process(line)); err != nil {
				return err
			}
		}
		joined = joined[:0]
		if e == io.EOF {
			break
		}
	}
	return writer.Flush()
}
func main() {
	if len(os.Args) != 3 {
		fmt.Fprintln(os.Stderr, "usage: program INPUT_JSONL OUTPUT_JSONL")
		os.Exit(2)
	}
	if err := run(os.Args[1], os.Args[2]); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

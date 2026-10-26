package main

import (
	"encoding/json"
	"fmt"
	"os"
	"strings"
)

type Entry struct {
	ID      string `json:"id"`
	Account string `json:"account"`
	Amount  int64  `json:"amount"`
}
type Request struct {
	Op        string      `json:"op"`
	Entries   []Entry     `json:"entries"`
	Nodes     []string    `json:"nodes"`
	Edges     [][2]string `json:"edges"`
	Expr      string      `json:"expr"`
	Intervals [][2]int32  `json:"intervals"`
}
type Account struct {
	Account string `json:"account"`
	Balance int64  `json:"balance"`
	Count   int    `json:"count"`
}
type LedgerResult struct {
	Accounts []Account `json:"accounts"`
	Accepted int       `json:"accepted"`
}
type ErrorResult struct {
	Error string `json:"error"`
}

func failure(s string) any { return ErrorResult{s} }
func evaluate(r Request) any {
	switch r.Op {
	case "merge":
		return merge(r.Intervals)
	case "ledger":
		return ledger(r.Entries)
	case "topo":
		return topo(r.Nodes, r.Edges)
	case "calc":
		p := parser{s: r.Expr}
		value := p.expression()
		p.skip()
		if p.pos != len(p.s) && p.err == "" {
			p.err = "syntax"
		}
		if p.err != "" {
			return failure(p.err)
		}
		return struct {
			Value int64 `json:"value"`
		}{value}
	default:
		return failure("unknown_op")
	}
}
func merge(intervals [][2]int32) any {
	for _, interval := range intervals {
		if interval[0] > interval[1] {
			return failure("invalid_interval")
		}
	}
	sortIntervals(intervals, make([][2]int32, len(intervals)))
	result := make([][2]int32, 0, len(intervals))
	for _, interval := range intervals {
		if len(result) == 0 || interval[0] > result[len(result)-1][1] {
			result = append(result, interval)
		} else if interval[1] > result[len(result)-1][1] {
			result[len(result)-1][1] = interval[1]
		}
	}
	return struct {
		Intervals [][2]int32 `json:"intervals"`
	}{result}
}

func sortIntervals(intervals, buffer [][2]int32) {
	if len(intervals) < 2 {
		return
	}
	mid := len(intervals) / 2
	sortIntervals(intervals[:mid], buffer[:mid])
	sortIntervals(intervals[mid:], buffer[mid:])
	i, j := 0, mid
	for k := range intervals {
		if i < mid && (j == len(intervals) || intervals[i][0] < intervals[j][0] ||
			(intervals[i][0] == intervals[j][0] && intervals[i][1] <= intervals[j][1])) {
			buffer[k] = intervals[i]
			i++
		} else {
			buffer[k] = intervals[j]
			j++
		}
	}
	copy(intervals, buffer)
}
func ledger(entries []Entry) any {
	seen := make(map[string]bool)
	accounts := make(map[string]*Account)
	accepted := 0
	for _, e := range entries {
		if seen[e.ID] {
			continue
		}
		seen[e.ID] = true
		name := strings.Trim(e.Account, " \t\n\r\v\f")
		if name == "" {
			return failure("empty_account")
		}
		a := accounts[name]
		if a == nil {
			a = &Account{Account: name}
			accounts[name] = a
		}
		a.Balance += e.Amount
		a.Count++
		accepted++
	}
	result := LedgerResult{Accounts: make([]Account, 0, len(accounts)), Accepted: accepted}
	names := &stringHeap{}
	for name := range accounts {
		names.Push(name)
	}
	for names.Len() > 0 {
		result.Accounts = append(result.Accounts, *accounts[names.Pop()])
	}
	return result
}

type stringHeap []string

func (h stringHeap) Len() int { return len(h) }
func (h *stringHeap) Push(x string) {
	*h = append(*h, x)
	for i := len(*h) - 1; i > 0; {
		parent := (i - 1) / 2
		if (*h)[parent] <= (*h)[i] {
			break
		}
		(*h)[parent], (*h)[i] = (*h)[i], (*h)[parent]
		i = parent
	}
}
func (h *stringHeap) Pop() string {
	result := (*h)[0]
	last := len(*h) - 1
	(*h)[0] = (*h)[last]
	*h = (*h)[:last]
	for i := 0; 2*i+1 < len(*h); {
		child := 2*i + 1
		if child+1 < len(*h) && (*h)[child+1] < (*h)[child] {
			child++
		}
		if (*h)[i] <= (*h)[child] {
			break
		}
		(*h)[i], (*h)[child] = (*h)[child], (*h)[i]
		i = child
	}
	return result
}
func topo(nodes []string, edges [][2]string) any {
	indegree := make(map[string]int, len(nodes))
	adjacent := make(map[string][]string)
	for _, n := range nodes {
		indegree[n] = 0
	}
	seen := make(map[[2]string]bool)
	for _, e := range edges {
		if _, ok := indegree[e[0]]; !ok {
			return failure("unknown_node")
		}
		if _, ok := indegree[e[1]]; !ok {
			return failure("unknown_node")
		}
		if seen[e] {
			continue
		}
		seen[e] = true
		adjacent[e[0]] = append(adjacent[e[0]], e[1])
		indegree[e[1]]++
	}
	available := &stringHeap{}
	for _, n := range nodes {
		if indegree[n] == 0 {
			available.Push(n)
		}
	}
	order := make([]string, 0, len(nodes))
	for available.Len() > 0 {
		n := available.Pop()
		order = append(order, n)
		for _, next := range adjacent[n] {
			indegree[next]--
			if indegree[next] == 0 {
				available.Push(next)
			}
		}
	}
	if len(order) != len(nodes) {
		return failure("cycle")
	}
	return struct {
		Order []string `json:"order"`
	}{order}
}

type parser struct {
	s   string
	pos int
	err string
}

func (p *parser) skip() {
	for p.pos < len(p.s) {
		switch p.s[p.pos] {
		case ' ', '\t', '\n', '\r', '\v', '\f':
			p.pos++
		default:
			return
		}
	}
}
func (p *parser) expression() int64 {
	v := p.term()
	for p.err == "" {
		p.skip()
		if p.pos == len(p.s) || (p.s[p.pos] != '+' && p.s[p.pos] != '-') {
			break
		}
		op := p.s[p.pos]
		p.pos++
		right := p.term()
		if op == '+' {
			v += right
		} else {
			v -= right
		}
	}
	return v
}
func (p *parser) term() int64 {
	v := p.unary()
	for p.err == "" {
		p.skip()
		if p.pos == len(p.s) || (p.s[p.pos] != '*' && p.s[p.pos] != '/') {
			break
		}
		op := p.s[p.pos]
		p.pos++
		right := p.unary()
		if p.err != "" {
			return 0
		}
		if op == '*' {
			v *= right
		} else {
			if right == 0 {
				p.err = "division_by_zero"
				return 0
			}
			v /= right
		}
	}
	return v
}
func (p *parser) unary() int64 {
	negative := false
	p.skip()
	for p.pos < len(p.s) && (p.s[p.pos] == '+' || p.s[p.pos] == '-') {
		if p.s[p.pos] == '-' {
			negative = !negative
		}
		p.pos++
		p.skip()
	}
	v := p.primary()
	if negative {
		return -v
	}
	return v
}
func (p *parser) primary() int64 {
	p.skip()
	if p.pos == len(p.s) {
		p.err = "syntax"
		return 0
	}
	if p.s[p.pos] == '(' {
		p.pos++
		v := p.expression()
		if p.err != "" {
			return 0
		}
		p.skip()
		if p.pos == len(p.s) || p.s[p.pos] != ')' {
			p.err = "syntax"
			return 0
		}
		p.pos++
		return v
	}
	start := p.pos
	var v int64
	for p.pos < len(p.s) && p.s[p.pos] >= '0' && p.s[p.pos] <= '9' {
		v = v*10 + int64(p.s[p.pos]-'0')
		p.pos++
	}
	if p.pos == start {
		p.err = "syntax"
	}
	return v
}
func main() {
	if len(os.Args) != 2 {
		fmt.Fprintln(os.Stderr, "expected one JSON argument")
		os.Exit(1)
	}
	var r Request
	if err := json.Unmarshal([]byte(os.Args[1]), &r); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	encoded, err := json.Marshal(evaluate(r))
	if err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	fmt.Println(string(encoded))
}

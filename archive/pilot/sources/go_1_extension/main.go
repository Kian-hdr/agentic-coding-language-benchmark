package main

import (
	"cmp"
	"encoding/json"
	"fmt"
	"os"
	"slices"
	"strings"
)

type entry struct {
	ID      string `json:"id"`
	Account string `json:"account"`
	Amount  int64  `json:"amount"`
}
type request struct {
	Op        string      `json:"op"`
	Entries   []entry     `json:"entries"`
	Nodes     []string    `json:"nodes"`
	Edges     [][2]string `json:"edges"`
	Expr      string      `json:"expr"`
	Intervals [][2]int32  `json:"intervals"`
}
type failure struct {
	Error string `json:"error"`
}
type account struct {
	Account string `json:"account"`
	Balance int64  `json:"balance"`
	Count   int    `json:"count"`
}

const whitespace = " \t\n\r\v\f"

func ledger(entries []entry) any {
	seen := make(map[string]bool)
	groups := make(map[string]*account)
	accepted := 0
	for _, e := range entries {
		if seen[e.ID] {
			continue
		}
		seen[e.ID] = true
		name := strings.Trim(e.Account, whitespace)
		if name == "" {
			return failure{"empty_account"}
		}
		if groups[name] == nil {
			groups[name] = &account{Account: name}
		}
		groups[name].Balance += e.Amount
		groups[name].Count++
		accepted++
	}
	accounts := make([]account, 0, len(groups))
	for _, a := range groups {
		accounts = append(accounts, *a)
	}
	slices.SortFunc(accounts, func(a, b account) int { return strings.Compare(a.Account, b.Account) })
	return struct {
		Accounts []account `json:"accounts"`
		Accepted int       `json:"accepted"`
	}{accounts, accepted}
}

type names []string

func (n *names) push(v string) {
	*n = append(*n, v)
	i := len(*n) - 1
	for i > 0 {
		parent := (i - 1) / 2
		if (*n)[parent] <= (*n)[i] {
			break
		}
		(*n)[parent], (*n)[i] = (*n)[i], (*n)[parent]
		i = parent
	}
}
func (n *names) pop() string {
	v := (*n)[0]
	(*n)[0] = (*n)[len(*n)-1]
	*n = (*n)[:len(*n)-1]
	for i := 0; 2*i+1 < len(*n); {
		child := 2*i + 1
		if child+1 < len(*n) && (*n)[child+1] < (*n)[child] {
			child++
		}
		if (*n)[i] <= (*n)[child] {
			break
		}
		(*n)[i], (*n)[child] = (*n)[child], (*n)[i]
		i = child
	}
	return v
}
func topo(nodes []string, edges [][2]string) any {
	degree := make(map[string]int)
	for _, n := range nodes {
		degree[n] = 0
	}
	adj := make(map[string][]string)
	seen := make(map[[2]string]bool)
	for _, e := range edges {
		if _, ok := degree[e[0]]; !ok {
			return failure{"unknown_node"}
		}
		if _, ok := degree[e[1]]; !ok {
			return failure{"unknown_node"}
		}
		if seen[e] {
			continue
		}
		seen[e] = true
		degree[e[1]]++
		adj[e[0]] = append(adj[e[0]], e[1])
	}
	available := &names{}
	for n, d := range degree {
		if d == 0 {
			available.push(n)
		}
	}
	order := make([]string, 0, len(nodes))
	for len(*available) > 0 {
		n := available.pop()
		order = append(order, n)
		for _, next := range adj[n] {
			degree[next]--
			if degree[next] == 0 {
				available.push(next)
			}
		}
	}
	if len(order) != len(nodes) {
		return failure{"cycle"}
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
	for p.pos < len(p.s) && strings.IndexByte(whitespace, p.s[p.pos]) >= 0 {
		p.pos++
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
		r := p.term()
		if op == '+' {
			v += r
		} else {
			v -= r
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
		r := p.unary()
		if p.err != "" {
			break
		}
		if op == '*' {
			v *= r
		} else {
			if r == 0 {
				p.err = "division_by_zero"
				return 0
			}
			v /= r
		}
	}
	return v
}
func (p *parser) unary() int64 {
	sign := int64(1)
	for {
		p.skip()
		if p.pos == len(p.s) {
			p.err = "syntax"
			return 0
		}
		switch p.s[p.pos] {
		case '+':
			p.pos++
		case '-':
			sign = -sign
			p.pos++
		default:
			return sign * p.primary()
		}
	}
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
func calc(expr string) any {
	p := parser{s: expr}
	v := p.expression()
	p.skip()
	if p.err == "" && p.pos != len(expr) {
		p.err = "syntax"
	}
	if p.err != "" {
		return failure{p.err}
	}
	return struct {
		Value int64 `json:"value"`
	}{v}
}
func merge(intervals [][2]int32) any {
	for _, interval := range intervals {
		if interval[0] > interval[1] {
			return failure{"invalid_interval"}
		}
	}
	slices.SortFunc(intervals, func(a, b [2]int32) int {
		return cmp.Compare(a[0], b[0])
	})
	merged := make([][2]int32, 0, len(intervals))
	for _, interval := range intervals {
		if len(merged) == 0 || interval[0] > merged[len(merged)-1][1] {
			merged = append(merged, interval)
		} else if interval[1] > merged[len(merged)-1][1] {
			merged[len(merged)-1][1] = interval[1]
		}
	}
	return struct {
		Intervals [][2]int32 `json:"intervals"`
	}{merged}
}

func execute(r request) any {
	switch r.Op {
	case "ledger":
		return ledger(r.Entries)
	case "topo":
		return topo(r.Nodes, r.Edges)
	case "calc":
		return calc(r.Expr)
	case "merge":
		return merge(r.Intervals)
	default:
		return failure{"unknown_op"}
	}
}
func main() {
	if len(os.Args) != 2 {
		fmt.Fprintln(os.Stderr, "expected one JSON argument")
		os.Exit(1)
	}
	var r request
	if err := json.Unmarshal([]byte(os.Args[1]), &r); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
	if err := json.NewEncoder(os.Stdout).Encode(execute(r)); err != nil {
		fmt.Fprintln(os.Stderr, err)
		os.Exit(1)
	}
}

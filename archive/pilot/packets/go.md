# Go benchmark implementation packet

Use Go 1.27.3 and its standard library. Implement the supplied task, not just the sample.

Compiler: `{ORIGINAL_BENCHMARK_ROOT}/toolchains/go/go/bin/go`
Set `GOTOOLCHAIN=local`, and `GOCACHE={ORIGINAL_BENCHMARK_ROOT}/toolchains/go/cache`. This prevents automatic toolchain download and reuses a warmed standard-library compilation cache.

The verified starter is `{ORIGINAL_BENCHMARK_ROOT}/toolchains/go/template`; copy its `go.mod` and `main.go` to your assigned directory. Replace the echo logic with the requested implementation. No third-party dependencies.

Build with:

```sh
GOTOOLCHAIN=local GOCACHE={ORIGINAL_BENCHMARK_ROOT}/toolchains/go/cache {ORIGINAL_BENCHMARK_ROOT}/toolchains/go/go/bin/go build -o program main.go
```

Create executable `run.sh` in your assigned directory. It must accept one request-file path, read its JSON content, and pass it to your program as a single argument. Return exactly one JSON value on stdout. Send diagnostics to stderr. The final `run.sh` should compile if necessary and work from any caller directory.

Input parsing can use `encoding/json.Unmarshal([]byte(os.Args[1]), &request)`; output can use `json.Marshal(response)` then `fmt.Println(string(encoded))`. Use task-specific structs with JSON field tags, `json.RawMessage`, or `map[string]any`; untyped JSON numbers decode to `float64`, so preserve integer semantics deliberately. `Decoder.UseNumber` supports retaining numeric text when relevant. Slices and maps are available in the standard library; use `sort`, `strings`, `strconv`, `math`, `unicode` as needed. `go test ./...` runs tests; `go vet ./...` performs additional checks; `gofmt` formats source. `go doc encoding/json` gives installed API documentation.

Primary docs: https://pkg.go.dev/encoding/json and https://go.dev/doc/.

The authoritative task is SPEC.md. The OLD packet below describes compiler paths/syntax only; ignore its old single-request run.sh / argument protocol. Implement new build.sh and one persistent worker.sh INPUT_JSONL OUTPUT_JSONL. All task computation and file parsing/serialization in assigned language.

# Kotlin/JVM baseline

Kotlin compiler 2.4.21 installed locally. Existing JDK 21.0.12.1 reused read-only; no global configuration changed. Implement `Main.kt` with `fun main(args: Array<String>)`. Read request filename `args[0]` with `java.io.File(args[0]).readText()`. Print exactly one JSON value. Use `org.json` 20260814 (preinstalled infrastructure dependency); no application logic may go in a different language.

Compile:
```sh
JAVA_HOME={ORIGINAL_HOMEBREW}/opt/openjdk@21 {ORIGINAL_BENCHMARK_ROOT}/toolchains/kotlin/kotlinc/bin/kotlinc Main.kt -jvm-target 21 -classpath {ORIGINAL_BENCHMARK_ROOT}/toolchains/kotlin/json-20260814.jar -include-runtime -d app.jar
```
Run:
```sh
{ORIGINAL_HOMEBREW}/opt/openjdk@21/bin/java -cp app.jar:{ORIGINAL_BENCHMARK_ROOT}/toolchains/kotlin/json-20260814.jar MainKt request.json
```
`run.sh` should resolve its directory and run the JVM with an absolute `app.jar` classpath and supplied request path; compile during development and ensure the latest source is built. For simple local tests use `check(condition)` / `require(condition)` or Kotlin assertions with JVM `-ea`.

JSON: `val req = JSONObject(File(args[0]).readText())`; `req.getString("field")`, `getLong`, `getInt`, `getJSONArray`, `getJSONObject`, `has`, `isNull`. `val a = req.getJSONArray("values"); for (i in 0 until a.length()) { a.getLong(i) }`. Build `JSONObject().put("field", value)` and `JSONArray().put(value)`, then `.toString()` for JSON. Use `JSONObject.NULL` for explicit null (passing Java/Kotlin null to JSONObject.put removes the field). No Kotlin-specific JSON compiler plugin required.

Kotlin standard library supports lists/maps, mutableListOf/mutableMapOf, map/filter/fold/groupBy/sortedWith, String regex, priority queues via java.util.PriorityQueue, and file APIs via java.io/java.nio. Use Long where numeric ranges warrant; Int/Long division truncates toward zero. Nullable types `T?`, `?.`, `?:`, smart casts; avoid `!!` without validation. Comparator construction `compareBy<T> { it.field }.thenBy { it.other }`.

Official docs: https://kotlinlang.org/docs/command-line.html and https://kotlinlang.org/docs/home.html
JSON API: https://stleary.github.io/JSON-java/org/json/JSONObject.html

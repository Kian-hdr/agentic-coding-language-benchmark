# Kotlin evaluation setup and continuity evidence

Verified 26 October 2026. Kotlin is an established general-purpose baseline, not an agent-specific language.

## Installation and actual execution

Downloaded pinned official compiler 2.4.21 from https://github.com/JetBrains/kotlin/releases/download/v2.4.21/kotlin-compiler-2.4.21.zip and official `.sha256`; checksum verified before extraction. Official release API says published 8 Oct 2026. Compiler installed solely under `toolchains/kotlin/kotlinc`.

Reused existing Homebrew OpenJDK 21.0.12.1 at `{ORIGINAL_HOMEBREW}/opt/openjdk@21`. Global `/usr/bin/java` is older Oracle 8, so commands must explicitly select JDK 21. No JDK installation or global PATH/JAVA_HOME changes were made.

Installed JSON-java `org.json:json:20260814` JAR locally from Maven Central and verified published SHA256. This established dependency-free JSON implementation is an infrastructure exception because Kotlin stdlib has no JSON parser. Official source/license: https://github.com/stleary/JSON-java ; project describes public-domain terms. Stored jar `{ORIGINAL_BENCHMARK_ROOT}/toolchains/kotlin/json-20260814.jar`.

`kotlinc -version` returns Kotlin/JVM 2.4.21 JRE 21.0.12.1. Smoke Main.kt was compiled with JVM target 21, classpath JSON JAR and include-runtime. Actual JVM execution read request.json `{"values":[1,2,3]}` and emitted exactly `{"total":6}`, exit 0. Files under `toolchains/kotlin/smoke`. No model benchmark run by setup worker.

Exact setup, run commands, neutral language/API notes: `packets/kotlin.md`.

## Codex compatibility and evidence limits

Codex can use the normal compiler, files and deterministic JVM CLI. No model-specific plugin is needed for this baseline. Do not infer GPT-6.1 Sol-specific training or superiority: no such primary evidence was established. JVM compilation startup and runtime should be distinguished from algorithm execution time. Kotlin/Native and Android were not installed or benchmarked; results will apply to this Kotlin/JVM configuration.

## Continuity and exit risk

Official FAQ records development since 2010, stable 1.0 in February 2016, Apache-2.0 source, a 100+ JetBrains engineering team and 250+ outside contributors. Treat team numbers as vendor-reported, not audited staffing. https://kotlinlang.org/docs/faq.html

The Kotlin Foundation is a nonprofit with a public governance structure. Its board includes JetBrains, Google, Touchlab, Meta and an independent director; the language committee can reject incompatible changes or require deprecation procedures. This is stronger continuity and compatibility evidence than a sponsor logo alone. https://kotlinfoundation.org/structure/

The Foundation funds ecosystem work and lists current grants. https://kotlinfoundation.org/

Kotlin/JVM can directly use Java libraries and coexist with Java, substantially reducing ecosystem and incremental-adoption risk. Existing Android first-class support and mature Gradle/Maven options strengthen practical viability; these do not prove superior agent performance. Official FAQ and command-line guide: https://kotlinlang.org/docs/faq.html ; https://kotlinlang.org/docs/command-line.html

Assessment: low relative abandonment risk among evaluated emerging languages, with no guarantee of perpetual support. Stable JVM bytecode, an established Java ecosystem, permissive licensing and multi-organization governance provide credible fallback options. Rewriting Kotlin into another source language would still take work; binary interoperability is not free source translation.


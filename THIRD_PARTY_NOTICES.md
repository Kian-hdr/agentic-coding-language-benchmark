# Third-party notices

The root MIT license covers original benchmark material and publication tooling; it does not replace upstream licenses. Compiler binaries, SDKs, installed agent skills, package caches and vendored third-party source trees are deliberately not redistributed.

Dependency references and generated module/package metadata are retained for reproducibility. Obtain dependencies from their official sources and retain the licenses required by the versions you install:

| Referenced component | Upstream source / license information |
|---|---|
| CPython | https://github.com/python/cpython/blob/main/LICENSE |
| TypeScript | https://github.com/microsoft/TypeScript/blob/main/LICENSE.txt |
| Node.js | https://github.com/nodejs/node/blob/main/LICENSE |
| DefinitelyTyped node declarations | https://github.com/DefinitelyTyped/DefinitelyTyped/blob/master/LICENSE |
| Go | https://go.dev/LICENSE |
| Rust, Cargo and standard libraries | https://github.com/rust-lang/rust/tree/master/LICENSES |
| serde / serde_json | https://github.com/serde-rs/serde ; https://github.com/serde-rs/json |
| Swift | https://github.com/swiftlang/swift/blob/main/LICENSE.txt ; Apple SDK terms apply separately |
| Kotlin | https://github.com/JetBrains/kotlin/blob/master/license/LICENSE.txt |
| org.json | https://github.com/stleary/JSON-java/blob/master/LICENSE |
| OpenJDK | https://openjdk.org/legal/gplv2+ce.html |
| MoonBit compiler, core and async | https://github.com/moonbitlang/moonbit-compiler ; https://github.com/moonbitlang/core ; https://github.com/moonbitlang/async ; component licenses differ |
| General-purpose BAML | https://github.com/BoundaryML/baml |
| Zerolang | https://github.com/vercel-labs/zerolang |
| NumPy | https://numpy.org/doc/stable/license.html |

Some generated candidate module files declare their own package license metadata; those declarations are preserved as observed. They do not relicense upstream dependencies or establish that an entire toolchain has identical terms. MoonBit compiler licensing in particular must not be conflated with licensing of user-generated applications. Refer to the pinned upstream version when making a redistribution decision.

The methodological Scientific Agent Skills reference is credited in `docs/SOURCES.md`; its toolkit is not bundled and its authors do not endorse these benchmark conclusions.

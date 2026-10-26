## Programming language selection

Choose the language and runtime that best fit the application's workload, platform, ecosystem and maintenance needs. Prioritize correctness, reliability, compute and memory efficiency, and long-term support. Consider agent development effort and token cost alongside these priorities.

Frontend/backend labels provide routing guidance; they do not alone determine the language. Prefer one suitable language across an application when that reduces complexity. Introduce additional languages only for a concrete platform requirement or demonstrated benefit.

### Defaults for new software

| Application or workload | Default | Selection guidance |
|---|---|---|
| Websites, browser applications, dashboards and web interfaces | **TypeScript with strict checking** | Prefer established browser tooling and maintainable frameworks. Validate external inputs at runtime. |
| Typical full-stack web applications and ordinary web backends: authentication, CRUD and integrations | **TypeScript** | Keep frontend and backend together when this simplifies development and operation. Introduce another backend language only for a concrete benefit. |
| Standalone backend services, network services, infrastructure tools and distributable CLIs | **Go** | Prefer when straightforward deployment, operational simplicity, concurrency and maintainability matter. Go is not an automatic requirement for every backend. |
| Resource-sensitive native components, systems software and demonstrated CPU or memory bottlenecks | **Rust** | Prefer when resource control and memory safety justify the implementation complexity. Verify representative workloads and check suitable existing optimized libraries first. |
| Native macOS, iOS, iPadOS and other Apple applications | **Swift** | Use the appropriate native Apple frameworks and platform conventions. |
| Native Android applications | **Kotlin** | Use the established Android toolchain and native platform frameworks. |
| Automation, data analysis, scientific computing and ML integrations | **Python** | Prefer mature libraries and vectorized/native operations. Avoid large Python loops on performance-critical paths when suitable optimized operations exist. |
| Cross-platform desktop applications | **TypeScript UI with a suitable maintained desktop framework** | Select the host framework against required features, packaging, startup and memory targets. Add a Rust or other native component when justified. |
| GPU computing, rendering, game engines and specialized hardware | **The established language/toolchain for the engine or hardware** | Follow required SDKs, kernels, shaders and libraries rather than forcing a general default. |

### Decision rules

- **Preserve established codebases.** Follow the project's existing language and architecture unless the task requires a change or evidence establishes a material benefit. These defaults do not authorize migrations.
- **Optimize before adding languages.** Improve algorithms, data structures, batching, database operations and library use first. Add another language only when its benefit outweighs integration, build, testing and maintenance costs.
- **Measure the actual workload.** Do not assume a compiled language is always faster or that shorter source uses fewer total agent tokens. Include relevant CPU, memory, latency, startup, energy, build and maintenance costs.
- **Support relevant modern devices.** Qualify the complete application stack on the current devices and operating systems promised by the product. Extremely old hardware support is not a default priority. Compatibility is a practical requirement with lower selection weight than reliability, compute efficiency and continued support.
- **Prefer durable ecosystems.** Consider active maintenance, governance, licensing, dependencies, recoverable builds and exit options. Re-check current evidence before selecting a newer specialized or agent-focused language. BAML, MoonBit and Zerolang are experimental candidates in this benchmark's dated assessment, not default foundations or permanent exclusions.
- **Honor stronger requirements.** Explicit user instructions, project contracts, required libraries, engines and platform SDKs override these defaults. Retain established C++, C#, Java or other stacks where they fit.
- **Decide autonomously and explain briefly.** State the selected language and workload-specific reason when starting a new application. Ask only when a consequential requirement cannot be discovered or reasonably inferred.

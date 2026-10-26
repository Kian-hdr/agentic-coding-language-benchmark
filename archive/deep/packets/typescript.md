The authoritative task is SPEC.md. The OLD packet below describes compiler paths/syntax only; ignore its old single-request run.sh / argument protocol. Implement new build.sh and one persistent worker.sh INPUT_JSONL OUTPUT_JSONL. All task computation and file parsing/serialization in assigned language.

# TypeScript baseline
Node {ORIGINAL_HOMEBREW}/bin/node v26.0.0. TypeScript 7.0.2 locally installed at:
{ORIGINAL_BENCHMARK_ROOT}/toolchains/typescript/node_modules/typescript
Node type declarations installed in sibling @types/node.
Use strict TypeScript and standard Node APIs only. No npm installs.

Compiler:
{ORIGINAL_BENCHMARK_ROOT}/toolchains/typescript/node_modules/.bin/tsc

Use tsconfig.json with strict:true, target:ES2022, module:NodeNext,
moduleResolution:NodeNext, types:["node"], typeRoots pointing at the absolute
toolchains/typescript/node_modules/@types directory, outDir:"dist".
TypeScript 7 may require ignoreConfig if mixing positional files and tsconfig;
prefer tsc -p tsconfig.json. Node fs.readFileSync handles request file input;
JSON.stringify outputs responses. run.sh should execute compiled JS; compile
before final completion so execution does not compile on every request.
Use Math.trunc(a / b) for division toward zero. Standard arrays, Map, Set and
node:assert are available. Business logic must remain in TypeScript.

import { readFileSync } from "node:fs";
import { operate } from "./operations.js";

const request: unknown = JSON.parse(readFileSync(process.argv[2], "utf8"));
process.stdout.write(JSON.stringify(operate(request)) + "\n");

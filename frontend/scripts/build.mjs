import { spawn } from "node:child_process";
import { access } from "node:fs/promises";
import path from "node:path";

async function hasFirebaseIndex() {
  try {
    await access(path.resolve("dist/client/index.html"));
    return true;
  } catch {
    return false;
  }
}

const viteBin = path.resolve("node_modules/vite/bin/vite.js");
const child = spawn(process.execPath, [viteBin, "build", ...process.argv.slice(2)], {
  stdio: ["inherit", "pipe", "pipe"],
});

let output = "";
child.stdout.on("data", (chunk) => {
  const text = chunk.toString();
  output += text;
  process.stdout.write(chunk);
});
child.stderr.on("data", (chunk) => {
  const text = chunk.toString();
  output += text;
});

const exitCode = await new Promise((resolve) => child.on("close", resolve));
if (exitCode === 0) {
  process.exit(0);
}

const handledViteTeardown =
  output.includes("process.stdin.off is not a function") &&
  output.includes("[prerender] Prerendered") &&
  (await hasFirebaseIndex());

if (!handledViteTeardown) {
  process.stderr.write(output);
  process.exit(exitCode ?? 1);
}

process.stderr.write("Ignored Vite stdin teardown after successful prerender artifact generation.\n");
process.exit(0);

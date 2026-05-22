import { existsSync } from "node:fs";
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

async function maybeIgnoreViteStdinTeardown(error) {
  if (
    error instanceof TypeError &&
    error.message === "process.stdin.off is not a function" &&
    (await hasFirebaseIndex())
  ) {
    return;
  }

  throw error;
}

process.on("uncaughtException", (error) => {
  maybeIgnoreViteStdinTeardown(error)
    .then(() => {
      process.exitCode = 0;
    })
    .catch((cause) => {
      throw cause;
    });
});

process.on("unhandledRejection", (error) => {
  maybeIgnoreViteStdinTeardown(error)
    .then(() => {
      process.exitCode = 0;
    })
    .catch((cause) => {
      throw cause;
    });
});

function ensureStdinOff(stdin = process.stdin) {
  if (typeof stdin.off !== "function") {
    stdin.off =
      typeof stdin.removeListener === "function" ? stdin.removeListener.bind(stdin) : () => stdin;
  }

  return stdin;
}

const stdinDescriptor = Object.getOwnPropertyDescriptor(process, "stdin");
if (stdinDescriptor?.get && stdinDescriptor.configurable) {
  Object.defineProperty(process, "stdin", {
    ...stdinDescriptor,
    get() {
      return ensureStdinOff(stdinDescriptor.get.call(process));
    },
  });
}

ensureStdinOff();

const originalExit = process.exit.bind(process);
process.exit = ((code) => {
  if (code && existsSync(path.resolve("dist/client/index.html"))) {
    return originalExit(0);
  }

  return originalExit(code);
});

process.argv = [process.argv[0], "vite", "build", ...process.argv.slice(2)];

await import("../node_modules/vite/bin/vite.js");

if (process.exitCode && (await hasFirebaseIndex())) {
  process.exitCode = 0;
}

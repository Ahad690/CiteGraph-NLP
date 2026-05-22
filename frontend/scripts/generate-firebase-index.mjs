import { readdir, readFile, writeFile } from "node:fs/promises";
import path from "node:path";

const clientDir = path.resolve("dist/client");
const assetsDir = path.join(clientDir, "assets");

const assetNames = await readdir(assetsDir);
const jsAssets = assetNames.filter((name) => name.endsWith(".js"));
const cssAssets = assetNames.filter((name) => name.endsWith(".css"));

let entryScript;
for (const asset of jsAssets) {
  const content = await readFile(path.join(assetsDir, asset), "utf8");
  if (content.includes("hydrateRoot(document")) {
    entryScript = asset;
    break;
  }
}

if (!entryScript) {
  throw new Error("Could not find the TanStack Start client entry bundle.");
}

const stylesheet = cssAssets.find((name) => name.startsWith("styles-")) ?? cssAssets[0];

const html = `<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>CiteGraph-NLP - Research Graph Intelligence</title>
    <meta name="description" content="Confidence-aware citation lineage and study-scale research analysis." />
    ${stylesheet ? `<link rel="stylesheet" href="/assets/${stylesheet}" />` : ""}
  </head>
  <body>
    <script type="module" src="/assets/${entryScript}"></script>
  </body>
</html>
`;

await writeFile(path.join(clientDir, "index.html"), html, "utf8");
console.log(`Generated dist/client/index.html using ${entryScript}`);

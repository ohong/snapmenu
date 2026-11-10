// Includes runtime, QA, dependencies, and corpus bytes; excludes docs and generated builds.
import { execFileSync } from "node:child_process";
import { createHash } from "node:crypto";
import { existsSync, readFileSync } from "node:fs";
const files = [
  ...new Set(
    execFileSync("git", ["ls-files", "-co", "--exclude-standard", "-z"], {
      encoding: "utf8",
    })
      .split("\0")
      .filter(Boolean),
  ),
]
  .filter(
    (path) =>
      existsSync(path) &&
      !path.endsWith(".md") &&
      (/^(src|frontend|static|migrations|tests|evals|scripts)\//.test(path) ||
        [
          "package.json",
          "package-lock.json",
          "tsconfig.json",
          "vite.config.ts",
          "wrangler.jsonc",
          "pytest.ini",
          "requirements-dev.txt",
        ].includes(path)),
  )
  .sort();
const hash = createHash("sha256");
for (const path of files)
  hash.update(path).update("\0").update(readFileSync(path)).update("\0");
console.log(
  JSON.stringify({ sha256: hash.digest("hex"), files: files.length }),
);

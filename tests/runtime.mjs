// Real Node API + Neon + private Vercel Blob. Only paid external HTTP is simulated.
import { createServer } from "node:http";
import { neon } from "@neondatabase/serverless";
import { list, del } from "@vercel/blob";
import app from "../src/app.ts";
import { database, imageStore } from "../src/storage.ts";
import { randomUUID } from "node:crypto";
import { readFileSync, existsSync } from "node:fs";
import { resolve, extname } from "node:path";
import assert from "node:assert/strict";
const stats = {
    scans: 0,
    image_submissions: 0,
    polls: 0,
    deletes: 0,
    cancels: 0,
    max_active: 0,
  },
  tasks = new Map();
let scenario = "ok",
  nextScenario = "ok";
const provider = process.env.TEST_PROVIDER || "muse";
const names = [
  "Hand Tossed Salad",
  "Roast Beef with Mushroom Sauce",
  "Loaded Baked Potato",
  "Roasted Vegetables",
  "Fruit Salad",
  "Strawberry Cake",
  "Peach & Blackberry Cobble",
  "Tea/Coffee/Capuccino",
  "Soft Drinks",
  "Juices",
];
const translated = [
  "Ensalada fresca",
  "Rosbif con salsa de champiñones",
  "Patata al horno",
  "Verduras asadas",
  "Ensalada de frutas",
  "Tarta de fresa",
  "Pastel de melocotón y moras",
  "Té/Café/Capuchino",
  "Refrescos",
  "Zumos",
];
function menu(es) {
  return {
    title: "Your menu",
    source_language: "English",
    warnings: [],
    dishes: names.map((name, i) => ({
      name_original: name,
      name_translated: es ? translated[i] : name,
      description_original: i === 0 ? "with ranch or thousand island" : "",
      description_translated:
        i === 0
          ? es
            ? "con aderezo ranch o mil islas"
            : "with ranch or thousand island"
          : "",
      price:
        i === 0 ? "7$ / 6$" : i === 8 ? "5$" : [7, 9].includes(i) ? "2$" : "7$",
      category:
        i === 0
          ? "Salads"
          : i < 5
            ? "Entrées"
            : i < 7
              ? "Desserts"
              : "Beverages",
      course:
        i === 0 ? "starter" : i < 5 ? "main" : i < 7 ? "dessert" : "drink",
    })),
  };
}
const image = readFileSync("tests/provider-image.webp").toString("base64");
async function external(req, init) {
  if (!(req instanceof Request)) req = new Request(req, init);
  const url = new URL(req.url);
  assert.equal(
    url.origin,
    provider === "muse" ? "https://api.meta.ai" : "https://api.openai.com",
  );
  assert.equal(req.headers.get("authorization"), `Bearer fixture-${provider}`);
  if (req.method === "DELETE") {
    stats.deletes++;
    return Response.json({ deleted: true });
  }
  if (url.pathname.endsWith("/cancel")) {
    stats.cancels++;
    return Response.json({ status: "cancelled" });
  }
  if (req.method === "POST") {
    const data = await req.json();
    assert.equal(data.safety_identifier.length, 64);
    if (data.tools) {
      stats.image_submissions++;
      assert.equal(data.background, true);
      assert.equal(data.store, true);
      if (provider === "muse") {
        assert.equal(data.model, "muse-image-1.0");
        assert.deepEqual(data.tools, [
          {
            type: "image_generation",
            enable_image_search: false,
            enable_web_search: false,
            enable_shell: false,
            reasoning_strength: "low",
            size: "1024x1024",
            output_format: "webp",
          },
        ]);
        assert.equal(data.reasoning, undefined);
      } else {
        assert.equal(data.model, "gpt-6-luna");
        assert.equal(data.tools[0].model, "gpt-image-2.5-flare");
        assert.equal(data.tool_choice.type, "image_generation");
      }
      scenario = nextScenario.startsWith("image_") ? nextScenario : "ok";
      if (nextScenario.startsWith("image_")) nextScenario = "ok";
      if (scenario === "image_timeout")
        throw Error("simulated transport failure");
      const task = "resp_fixture-" + stats.image_submissions;
      tasks.set(task, { scenario, polls: 0 });
      stats.max_active = Math.max(
        stats.max_active,
        [...tasks.values()].filter((t) => t.polls < 2).length,
      );
      return Response.json({ id: task, status: "queued", output: [] });
    }
    stats.scans++;
    assert.equal(
      data.model,
      provider === "muse" ? "muse-ember-1.0" : "gpt-6-luna",
    );
    assert.equal(data.reasoning.effort, "low");
    assert.equal(data.store, false);
    assert.equal(data.text.format.strict, true);
    assert.equal(data.text.format.type, "json_schema");
    scenario = nextScenario.startsWith("image_") ? "ok" : nextScenario;
    if (!nextScenario.startsWith("image_")) nextScenario = "ok";
    if (scenario === "scan_unavailable")
      return Response.json({ error: "fixture" }, { status: 503 });
    let result = menu(data.instructions.includes("Español"));
    if (scenario === "empty") result.dishes = [];
    if (scenario === "unreadable") delete result.dishes[0].price;
    if (scenario === "unsafe_text")
      result.dishes[0].name_translated = '<img src=x onerror="alert(1)">';
    return Response.json({
      id: "resp_scan",
      status: scenario === "truncated" ? "incomplete" : "completed",
      output: [
        {
          type: "message",
          content:
            scenario === "refusal"
              ? [{ type: "refusal" }]
              : [{ type: "output_text", text: JSON.stringify(result) }],
        },
      ],
    });
  }
  stats.polls++;
  const task = tasks.get(url.pathname.split("/").at(-1));
  assert.ok(task);
  task.polls++;
  if (task.scenario === "image_failed")
    return Response.json({ status: "failed", output: [] });
  return Response.json(
    task.polls === 1
      ? { status: "in_progress", output: [] }
      : {
          status: "completed",
          output: [
            {
              type: "image_generation_call",
              status: "completed",
              result: task.scenario === "image_invalid" ? "invalid" : image,
            },
          ],
        },
  );
}

const schema = "qa_" + randomUUID().replaceAll("-", "");
const sql = neon(process.env.DATABASE_URL);
await sql.query(`CREATE SCHEMA "${schema}"`);
const ddl = readFileSync("migrations/0001_initial.sql", "utf8")
  .replace(/\b(scans|images|usage)\b/g, (name) => `"${schema}"."${name}"`)
  .split(";")
  .map((x) => x.trim())
  .filter(Boolean);
await sql.transaction(ddl.map((text) => sql.query(text)));
const prefix = "qa/" + schema + "/";
const env = {
  DB: database(process.env.DATABASE_URL, schema),
  IMAGES: imageStore(process.env.BLOB_READ_WRITE_TOKEN, prefix),
  AI_PROVIDER: provider,
  MODEL_API_KEY: "fixture-muse",
  OPENAI_API_KEY: "fixture-openai",
  DAILY_SCAN_LIMIT: "1000",
  DAILY_IMAGE_LIMIT: "1000",
  request: external,
  ASSETS: {
    async fetch(req) {
      const path = new URL(req.url).pathname;
      if (path === "/__fixture/stats") return Response.json(stats);
      if (path.startsWith("/__fixture/mode/")) {
        nextScenario = path.split("/").at(-1);
        return Response.json({ ok: true });
      }
      let file = resolve("dist", "." + (path === "/" ? "/index.html" : path));
      if (!file.startsWith(resolve("dist") + "/") || !existsSync(file))
        file = resolve("dist/index.html");
      return new Response(readFileSync(file), {
        headers: {
          "content-type":
            {
              ".html": "text/html",
              ".js": "text/javascript",
              ".mjs": "text/javascript",
              ".css": "text/css",
              ".svg": "image/svg+xml",
            }[extname(file)] || "application/octet-stream",
        },
      });
    },
  },
};
const server = createServer(async (req, res) => {
  try {
    const chunks = [];
    for await (const chunk of req) chunks.push(chunk);
    const request = new Request("http://" + req.headers.host + req.url, {
      method: req.method,
      headers: req.headers,
      body: ["GET", "HEAD"].includes(req.method)
        ? undefined
        : Buffer.concat(chunks),
    });
    const response = await app.fetch(request, env);
    res.writeHead(response.status, Object.fromEntries(response.headers));
    res.end(Buffer.from(await response.arrayBuffer()));
  } catch (error) {
    console.error(error.name, error.message);
    res.writeHead(500);
    res.end("Fixture failure");
  }
});
server.listen(Number(process.env.FIXTURE_PORT || 8788), "127.0.0.1", () =>
  console.log("Fixture ready"),
);
for (const signal of ["SIGTERM", "SIGINT"])
  process.on(signal, async () => {
    server.close();
    try {
      const objects = await list({
        prefix,
        token: process.env.BLOB_READ_WRITE_TOKEN,
      });
      if (objects.blobs.length)
        await del(
          objects.blobs.map((b) => b.url),
          { token: process.env.BLOB_READ_WRITE_TOKEN },
        );
      await sql.query(`DROP SCHEMA "${schema}" CASCADE`);
    } finally {
      process.exit();
    }
  });

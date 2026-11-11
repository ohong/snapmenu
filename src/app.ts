import {
  AppError,
  languages,
  provider,
  type Env,
  type Menu,
  type Provider,
  type ImageState,
} from "./models.js";
import {
  key,
  models,
  readMenu,
  startImage,
  request as aiRequest,
  removeResponse,
  imageBytes,
} from "./providers.js";
const now = () => Math.floor(Date.now() / 1000);
const id = () => crypto.randomUUID();
const json = (value: unknown, status = 200) => Response.json(value, { status });
async function hash(text: string) {
  return Array.from(
    new Uint8Array(
      await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text)),
    ),
    (b) => b.toString(16).padStart(2, "0"),
  ).join("");
}
function limit(value: string | undefined) {
  const n = Number(value ?? 100);
  if (!Number.isSafeInteger(n) || n < 0)
    throw new AppError(503, "The service limit setting is invalid.");
  return n;
}
async function body(request: Request, max = 4 * 1024 * 1024) {
  if (Number(request.headers.get("content-length") ?? 0) > max)
    throw new AppError(413, "Choose a smaller photo or PDF.");
  const reader = request.body?.getReader();
  if (!reader) throw new AppError(422, "Choose a menu first.");
  const chunks: Uint8Array[] = [];
  let size = 0;
  while (true) {
    const part = await reader.read();
    if (part.done) break;
    size += part.value.length;
    if (size > max) {
      await reader.cancel();
      throw new AppError(413, "Choose a smaller photo or PDF.");
    }
    chunks.push(part.value);
  }
  const bytes = new Uint8Array(size);
  let offset = 0;
  for (const part of chunks) {
    bytes.set(part, offset);
    offset += part.length;
  }
  try {
    return JSON.parse(new TextDecoder().decode(bytes));
  } catch {
    throw new AppError(
      422,
      "The upload could not be read. Please choose it again.",
    );
  }
}
// Client normalization avoids native codecs and large original-photo uploads in the API.
function validPage(page: unknown): page is string {
  if (
    typeof page !== "string" ||
    !/^data:image\/jpeg;base64,[A-Za-z0-9+/]+=*$/.test(page) ||
    page.length > 3 * 1024 * 1024
  )
    return false;
  try {
    const bytes = atob(page.slice(23));
    if (bytes.charCodeAt(0) !== 255 || bytes.charCodeAt(1) !== 216)
      return false;
    let i = 2;
    while (i < bytes.length - 9) {
      if (bytes.charCodeAt(i++) !== 255) return false;
      const marker = bytes.charCodeAt(i++);
      if (marker === 217 || marker === 218) break;
      const length = (bytes.charCodeAt(i) << 8) | bytes.charCodeAt(i + 1);
      if (length < 2) return false;
      if ([192, 193, 194].includes(marker)) {
        const h = (bytes.charCodeAt(i + 3) << 8) | bytes.charCodeAt(i + 4),
          w = (bytes.charCodeAt(i + 5) << 8) | bytes.charCodeAt(i + 6);
        return w > 0 && h > 0 && w <= 1800 && h <= 1800;
      }
      i += length;
    }
    return false;
  } catch {
    return false;
  }
}
interface ImageRow {
  menu_id: string;
  dish_id: string;
  provider: Provider;
  task_id: string | null;
  status: ImageState["status"];
  error: string;
  attempts: number;
  created_at: number;
  checked_at: number;
  lease_until: number;
}
function publicImage(row: ImageRow): ImageState {
  return {
    status: row.status,
    error: row.error,
    attempts: row.attempts,
    ...(row.status === "ready"
      ? { url: `/api/menus/${row.menu_id}/dishes/${row.dish_id}/picture` }
      : {}),
  };
}
async function owned(env: Env, menuId: string, owner: string): Promise<Menu> {
  const row = await env.DB.prepare(
    "SELECT payload FROM scans WHERE id=? AND owner=? AND status='ready' AND created_at>?",
  )
    .bind(menuId, owner, now() - 604800)
    .first<{ payload: string }>();
  if (!row)
    throw new AppError(
      404,
      "This menu has expired or is not available in this browser.",
    );
  const menu: Menu = JSON.parse(row.payload);
  const images = await env.DB.prepare("SELECT * FROM images WHERE menu_id=?")
    .bind(menuId)
    .all<ImageRow>();
  for (const dish of menu.dishes) {
    const image = images.results.find((x) => x.dish_id === dish.id);
    dish.image = image ? publicImage(image) : null;
  }
  return menu;
}
async function imageRow(env: Env, menuId: string, dishId: string) {
  return env.DB.prepare("SELECT * FROM images WHERE menu_id=? AND dish_id=?")
    .bind(menuId, dishId)
    .first<ImageRow>();
}
async function route(req: Request, env: Env, owner: string): Promise<Response> {
  const path = new URL(req.url).pathname,
    method = req.method,
    p = provider(env);
  if (path === "/api/health" && method === "GET") {
    await env.DB.prepare("SELECT 1 FROM scans LIMIT 1").first();
    return json({ status: "ok" });
  }
  if (path === "/api/config" && method === "GET")
    return json({
      languages,
      provider: p,
      reading_available: !!key(env, p),
      images_available: !!key(env, p),
      max_upload_mb: 10,
    });
  if (path === "/api/menus/latest" && method === "GET") {
    const row = await env.DB.prepare(
      "SELECT id FROM scans WHERE owner=? AND status='ready' AND created_at>? ORDER BY created_at DESC LIMIT 1",
    )
      .bind(owner, now() - 604800)
      .first<{ id: string }>();
    return json({ menu: row ? await owned(env, row.id, owner) : null });
  }
  if (path === "/api/menus" && method === "POST") {
    if (!key(env, p))
      throw new AppError(
        503,
        "Menu reading is not connected. Add the provider API key on the server.",
      );
    const started = performance.now(),
      data = await body(req);
    if (
      !Array.isArray(data.pages) ||
      data.pages.length < 1 ||
      data.pages.length > 3 ||
      !data.pages.every(validPage)
    )
      throw new AppError(
        422,
        "Choose 1–3 readable JPEG menu pages, no larger than 1800 pixels.",
      );
    if (typeof data.language !== "string" || !languages[data.language])
      throw new AppError(422, "Choose a supported language.");
    const fingerprint = await hash(
      p + models(env, p).menu + data.language + data.pages.join(""),
    );
    const previous = await env.DB.prepare(
      "SELECT id,status FROM scans WHERE owner=? AND fingerprint=?",
    )
      .bind(owner, fingerprint)
      .first<{ id: string; status: string }>();
    if (previous) {
      if (previous.status === "ready")
        return json(await owned(env, previous.id, owner));
      if (previous.status === "starting")
        throw new AppError(
          409,
          "This menu is already being read. Check your last menu shortly.",
        );
      // A new file selection is an explicit retry. Keep prior usage; never retry in the background.
      await env.DB.prepare(
        "DELETE FROM scans WHERE id=? AND owner=? AND status='failed'",
      )
        .bind(previous.id, owner)
        .run();
    }
    const menuId = id(),
      stamp = now();
    // Database batches are transactions. The claim and usage record either commit together or roll back.
    const results = await env.DB.batch([
      env.DB.prepare(
        `INSERT INTO scans(id,owner,fingerprint,created_at,status) SELECT ?,?,?,?,'starting'
 WHERE (SELECT count(*) FROM usage WHERE kind='scan' AND created_at>?)<?
 AND (SELECT count(*) FROM usage WHERE kind='scan' AND owner=? AND created_at>?)<?
 AND (SELECT count(*) FROM scans WHERE status='starting' AND created_at>?)<3 ON CONFLICT(owner,fingerprint) DO NOTHING`,
      ).bind(
        menuId,
        owner,
        fingerprint,
        stamp,
        stamp - 86400,
        limit(env.DAILY_SCAN_LIMIT),
        owner,
        stamp - 3600,
        limit(env.HOURLY_SCAN_LIMIT ?? "10"),
        stamp - 120,
      ),
      env.DB.prepare(
        "INSERT INTO usage SELECT ?,?,'scan',? WHERE EXISTS(SELECT 1 FROM scans WHERE id=?)",
      ).bind(menuId, owner, stamp, menuId),
    ]);
    if (!results[0].meta.changes)
      throw new AppError(
        429,
        "The scan limit was reached or this scan is already running. Try again later.",
      );
    const prepared = performance.now();
    try {
      const result = await readMenu(env, p, data.pages, data.language, owner);
      if (!result.dishes.length)
        throw new AppError(
          422,
          "No readable dishes found. Try a closer, well-lit photo.",
        );
      const menu: Menu = {
        ...result,
        id: menuId,
        language: data.language,
        created_at: stamp,
        dishes: result.dishes.map((dish, index) => ({
          ...dish,
          id: String(index + 1),
          image: null,
        })),
      };
      await env.DB.prepare(
        "UPDATE scans SET status='ready',payload=? WHERE id=?",
      )
        .bind(JSON.stringify(menu), menuId)
        .run();
      const response = json(menu);
      response.headers.set(
        "Server-Timing",
        `prepare;dur=${(prepared - started).toFixed(1)}, model;dur=${(performance.now() - prepared).toFixed(1)}`,
      );
      return response;
    } catch (error) {
      await env.DB.prepare("UPDATE scans SET status='failed' WHERE id=?")
        .bind(menuId)
        .run();
      throw error;
    }
  }
  const match = path.match(
    /^\/api\/menus\/([\w-]+)(?:\/dishes\/(\d+)\/(image|picture))?$/,
  );
  if (!match) throw new AppError(404, "Not found.");
  const [, menuId, dishId, action] = match;
  const menu = await owned(env, menuId, owner);
  if (!dishId) {
    if (method === "GET") return json(menu);
    if (method === "DELETE") {
      // Claims cannot land after this delete because image INSERT checks menu ownership and existence.
      const rows = await env.DB.prepare("SELECT * FROM images WHERE menu_id=?")
        .bind(menuId)
        .all<ImageRow>();
      await env.DB.prepare("DELETE FROM scans WHERE id=? AND owner=?")
        .bind(menuId, owner)
        .run();
      for (const row of rows.results) {
        if (row.task_id && row.status === "pending")
          await removeResponse(env, row.provider, row.task_id, true);
        await env.IMAGES.delete(`${menuId}/${row.dish_id}.webp`);
      }
      return json({ deleted: true });
    }
    throw new AppError(405, "Method not allowed.");
  }
  const dish = menu.dishes.find((x) => x.id === dishId);
  if (!dish) throw new AppError(404, "This dish is not on the menu.");
  let row = await imageRow(env, menuId, dishId);
  if (action === "picture" && method === "GET") {
    if (row?.status !== "ready")
      throw new AppError(404, "Picture is not ready.");
    const image = await env.IMAGES.get(`${menuId}/${dishId}.webp`);
    if (!image) throw new AppError(404, "Picture is not available.");
    return new Response(image.body, {
      headers: {
        "Content-Type": "image/webp",
        "Cache-Control": "private, max-age=3600",
        ETag: image.httpEtag,
      },
    });
  }
  if (action !== "image") throw new AppError(405, "Method not allowed.");
  if (method === "POST") {
    if (row && row.status !== "failed") return json(publicImage(row));
    if (!key(env, p))
      throw new AppError(
        503,
        "Dish pictures are not connected. You can still read every dish.",
      );
    const claim = id(),
      stamp = now();
    const results = await env.DB.batch([
      env.DB.prepare(
        `INSERT INTO images(menu_id,dish_id,provider,task_id,status,created_at)
 SELECT ?,?,?,?,'starting',? WHERE EXISTS(SELECT 1 FROM scans WHERE id=? AND owner=?)
 AND (SELECT count(*) FROM usage WHERE kind='image' AND created_at>?)<?
 AND (SELECT count(*) FROM usage WHERE kind='image' AND owner=? AND created_at>?)<?
 AND (SELECT count(*) FROM images WHERE status='starting' AND created_at>?)<12
 ON CONFLICT(menu_id,dish_id) DO UPDATE SET provider=excluded.provider,task_id=excluded.task_id,status='starting',error='',attempts=images.attempts+1,created_at=excluded.created_at,checked_at=0,lease_until=0
 WHERE images.status='failed' AND images.attempts<2`,
      ).bind(
        menuId,
        dishId,
        p,
        claim,
        stamp,
        menuId,
        owner,
        stamp - 86400,
        limit(env.DAILY_IMAGE_LIMIT),
        owner,
        stamp - 3600,
        limit(env.HOURLY_IMAGE_LIMIT ?? "20"),
        stamp - 120,
      ),
      env.DB.prepare(
        "INSERT INTO usage SELECT ?,?,'image',? WHERE EXISTS(SELECT 1 FROM images WHERE menu_id=? AND dish_id=? AND task_id=?)",
      ).bind(claim, owner, stamp, menuId, dishId, claim),
    ]);
    if (!results[0].meta.changes) {
      row = await imageRow(env, menuId, dishId);
      if (row && row.status !== "failed") return json(publicImage(row));
      throw new AppError(
        429,
        "The picture limit was reached. Keep browsing or try later.",
      );
    }
    try {
      const task = await startImage(env, p, dish, owner);
      const update = await env.DB.prepare(
        "UPDATE images SET status='pending',task_id=? WHERE menu_id=? AND dish_id=? AND task_id=?",
      )
        .bind(task, menuId, dishId, claim)
        .run();
      if (!update.meta.changes) {
        await removeResponse(env, p, task, true);
        throw new AppError(404, "This menu was deleted.");
      }
    } catch (error) {
      if (!(error instanceof AppError)) throw error;
      await env.DB.prepare(
        "UPDATE images SET status=?,error=? WHERE menu_id=? AND dish_id=? AND task_id=?",
      )
        .bind(
          error.uncertain ? "uncertain" : "failed",
          error.uncertain
            ? "This picture request could not be confirmed. Keep browsing."
            : error.message,
          menuId,
          dishId,
          claim,
        )
        .run();
    }
    row = await imageRow(env, menuId, dishId);
    if (!row) throw new AppError(404, "This menu was deleted.");
    return json(publicImage(row));
  }
  if (method === "GET") {
    if (!row) throw new AppError(404, "No picture was requested.");
    if (row.status === "starting" && now() - row.created_at > 120) {
      await env.DB.prepare(
        "UPDATE images SET status='uncertain',error='This picture request was interrupted. Keep browsing.' WHERE menu_id=? AND dish_id=? AND status='starting'",
      )
        .bind(menuId, dishId)
        .run();
      row = (await imageRow(env, menuId, dishId))!;
    }
    if (row.status !== "pending" || now() - row.checked_at < 1)
      return json(publicImage(row));
    const lease = await env.DB.prepare(
      "UPDATE images SET lease_until=?,checked_at=? WHERE menu_id=? AND dish_id=? AND lease_until<? AND status='pending'",
    )
      .bind(now() + 45, now(), menuId, dishId, now())
      .run();
    if (!lease.meta.changes) return json(publicImage(row));
    try {
      const result = await aiRequest(
        env,
        row.provider,
        `/responses/${row.task_id}`,
      );
      if (result.status === "completed") {
        let bytes: Uint8Array;
        try {
          bytes = imageBytes(result);
        } catch (error) {
          await env.DB.prepare(
            "UPDATE images SET status='failed',error='The picture was unreadable. You can try once more.' WHERE menu_id=? AND dish_id=?",
          )
            .bind(menuId, dishId)
            .run();
          await removeResponse(env, row.provider, row.task_id!);
          throw error;
        }
        // Store first, then mark ready. A storage failure keeps the retrievable provider task pending.
        await env.IMAGES.put(`${menuId}/${dishId}.webp`, bytes, {
          httpMetadata: { contentType: "image/webp" },
        });
        const update = await env.DB.prepare(
          "UPDATE images SET status='ready',error='' WHERE menu_id=? AND dish_id=?",
        )
          .bind(menuId, dishId)
          .run();
        if (!update.meta.changes)
          await env.IMAGES.delete(`${menuId}/${dishId}.webp`);
        await removeResponse(env, row.provider, row.task_id!);
      } else if (
        ["failed", "cancelled", "incomplete"].includes(result.status)
      ) {
        await env.DB.prepare(
          "UPDATE images SET status='failed',error='This dish picture could not be made.' WHERE menu_id=? AND dish_id=?",
        )
          .bind(menuId, dishId)
          .run();
        await removeResponse(env, row.provider, row.task_id!);
      }
    } catch (error) {
      console.warn(
        "Image retrieval failed",
        row.provider,
        error instanceof AppError ? error.status : "storage",
      );
    } finally {
      await env.DB.prepare(
        "UPDATE images SET lease_until=0 WHERE menu_id=? AND dish_id=?",
      )
        .bind(menuId, dishId)
        .run();
    }
    row = await imageRow(env, menuId, dishId);
    if (!row) throw new AppError(404, "This menu was deleted.");
    return json(publicImage(row));
  }
  throw new AppError(405, "Method not allowed.");
}
export default {
  async fetch(req: Request, env: Env): Promise<Response> {
    if (!new URL(req.url).pathname.startsWith("/api/"))
      return env.ASSETS.fetch(req);
    let token = req.headers
      .get("cookie")
      ?.match(/(?:^|;\s*)snapmenu_session=([\w-]{36,64})(?:;|$)/)?.[1];
    const fresh = !token;
    if (!token) token = (id() + id()).replaceAll("-", "");
    let response: Response;
    try {
      const origin = req.headers.get("origin");
      if (
        !["GET", "HEAD", "OPTIONS"].includes(req.method) &&
        origin &&
        origin !== new URL(req.url).origin
      )
        throw new AppError(403, "Open SnapMenu in its own browser tab.");
      response = await route(req, env, await hash(token));
    } catch (error) {
      if (!(error instanceof AppError))
        console.error(
          "Request failed",
          error instanceof Error ? error.name : "unknown",
        );
      response = json(
        {
          detail:
            error instanceof AppError
              ? error.message
              : "Something went wrong. Please try again later.",
        },
        error instanceof AppError ? error.status : 500,
      );
    }
    response.headers.set("X-Content-Type-Options", "nosniff");
    response.headers.set(
      "Cache-Control",
      response.headers.get("Cache-Control") || "no-store",
    );
    response.headers.set("Referrer-Policy", "no-referrer");
    if (
      fresh &&
      !["/api/config", "/api/health"].includes(new URL(req.url).pathname)
    )
      response.headers.append(
        "Set-Cookie",
        `snapmenu_session=${token}; HttpOnly; SameSite=Lax; Path=/; Max-Age=604800${new URL(req.url).protocol === "https:" ? "; Secure" : ""}`,
      );
    return response;
  },
  async scheduled(_event: unknown, env: Env) {
    const expired = await env.DB.prepare(
      "SELECT * FROM images WHERE menu_id IN (SELECT id FROM scans WHERE created_at<?)",
    )
      .bind(now() - 604800)
      .all<ImageRow>();
    for (const row of expired.results) {
      if (row.task_id && row.status === "pending")
        await removeResponse(env, row.provider, row.task_id, true);
      await env.IMAGES.delete(`${row.menu_id}/${row.dish_id}.webp`);
    }
    await env.DB.batch([
      env.DB.prepare("DELETE FROM scans WHERE created_at<?").bind(
        now() - 604800,
      ),
      env.DB.prepare("DELETE FROM usage WHERE created_at<?").bind(
        now() - 86400,
      ),
    ]);
  },
};

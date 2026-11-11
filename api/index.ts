import app from "../src/app.js";
import { environment } from "../src/environment.js";
export const maxDuration = 120;
async function handle(request: Request): Promise<Response> {
  if (new URL(request.url).pathname === "/api/maintenance") {
    if (
      !process.env.CRON_SECRET ||
      request.headers.get("authorization") !==
        "Bearer " + process.env.CRON_SECRET
    )
      return new Response("Unauthorized", { status: 401 });
    await app.scheduled(null, environment());
    return Response.json({ ok: true });
  }
  return app.fetch(request, environment());
}

export default { fetch: handle };

import { database, imageStore } from "./storage.js";
import type { Env } from "./models.js";
let cached: Env;
export function environment(): Env {
  if (!cached) {
    if (!process.env.DATABASE_URL || !process.env.BLOB_READ_WRITE_TOKEN)
      throw Error("Storage is not configured");
    cached = {
      ...process.env,
      DB: database(process.env.DATABASE_URL),
      IMAGES: imageStore(process.env.BLOB_READ_WRITE_TOKEN),
      ASSETS: {
        async fetch() {
          return new Response("Not found", { status: 404 });
        },
      },
    };
  }
  return cached;
}

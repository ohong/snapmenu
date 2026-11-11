import { neon } from "@neondatabase/serverless";
import { get, put, del } from "@vercel/blob";
export interface QueryResult<T = unknown> {
  results: T[];
  meta: { changes: number };
}
export interface Statement {
  bind(...values: unknown[]): Statement;
  first<T>(): Promise<T | null>;
  all<T>(): Promise<QueryResult<T>>;
  run(): Promise<QueryResult>;
}
export interface Database {
  prepare(text: string): Statement;
  batch(statements: Statement[]): Promise<QueryResult[]>;
}
export interface ImageStore {
  get(
    path: string,
  ): Promise<{ body: ReadableStream<Uint8Array>; httpEtag: string } | null>;
  put(path: string, bytes: Uint8Array, options?: unknown): Promise<void>;
  delete(path: string): Promise<void>;
}
// Parameters are numbered outside SQL string literals, so stored error text is never rewritten.
function numbered(text: string) {
  let n = 0;
  return text.replace(/'(?:''|[^'])*'|\?/g, (part) =>
    part === "?" ? "$" + ++n : part,
  );
}
export function database(url: string, schema = "public"): Database {
  if (!/^[a-z][a-z0-9_]*$/.test(schema)) throw Error("Invalid database schema");
  const sql = neon(url, { fullResults: true });
  const qualify = (text: string) =>
    text.replace(
      /\b(scans|images|usage)\b/g,
      (name) => `"${schema}"."${name}"`,
    );
  class Query implements Statement {
    constructor(
      public text: string,
      public values: unknown[] = [],
    ) {}
    bind(...values: unknown[]) {
      return new Query(this.text, values);
    }
    async all<T>(): Promise<QueryResult<T>> {
      const r = await sql.query(qualify(numbered(this.text)), this.values);
      return { results: r.rows as T[], meta: { changes: r.rowCount ?? 0 } };
    }
    async first<T>() {
      return (await this.all<T>()).results[0] ?? null;
    }
    async run() {
      return this.all();
    }
  }
  return {
    prepare: (text) => new Query(text),
    async batch(statements) {
      // Serialize short quota/claim transactions in Postgres, never the external model calls.
      const queries = statements.map((value) => {
        const q = value as Query;
        return sql.query(qualify(numbered(q.text)), q.values);
      });
      const result = await sql.transaction([
        sql.query("SELECT pg_advisory_xact_lock(73492018)"),
        ...queries,
      ]);
      return result
        .slice(1)
        .map((r) => ({ results: r.rows, meta: { changes: r.rowCount ?? 0 } }));
    },
  };
}
export function imageStore(token: string, prefix = ""): ImageStore {
  return {
    async get(path) {
      const r = await get(prefix + path, {
        access: "private",
        token,
        useCache: false,
      });
      return r?.statusCode === 200
        ? { body: r.stream, httpEtag: r.blob.etag }
        : null;
    },
    async put(path, bytes) {
      await put(prefix + path, Buffer.from(bytes), {
        access: "private",
        token,
        contentType: "image/webp",
        addRandomSuffix: false,
        allowOverwrite: true,
      });
    },
    async delete(path) {
      await del(prefix + path, { token });
    },
  };
}

CREATE TABLE IF NOT EXISTS scans (
 id TEXT PRIMARY KEY, owner TEXT NOT NULL, fingerprint TEXT NOT NULL,
 created_at INTEGER NOT NULL, status TEXT NOT NULL, payload TEXT,
 UNIQUE(owner, fingerprint)
);
CREATE INDEX IF NOT EXISTS scans_created ON scans(created_at);
CREATE INDEX IF NOT EXISTS scans_owner ON scans(owner, created_at);
CREATE TABLE IF NOT EXISTS images (
 menu_id TEXT NOT NULL REFERENCES scans(id) ON DELETE CASCADE,
 dish_id TEXT NOT NULL, provider TEXT NOT NULL, task_id TEXT,
 status TEXT NOT NULL, error TEXT NOT NULL DEFAULT '',
 attempts INTEGER NOT NULL DEFAULT 1, created_at INTEGER NOT NULL,
 checked_at INTEGER NOT NULL DEFAULT 0, lease_until INTEGER NOT NULL DEFAULT 0,
 PRIMARY KEY(menu_id, dish_id)
);
CREATE INDEX IF NOT EXISTS images_created ON images(created_at);
CREATE TABLE IF NOT EXISTS usage (
 id TEXT PRIMARY KEY, owner TEXT NOT NULL, kind TEXT NOT NULL, created_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS usage_time ON usage(kind,created_at);

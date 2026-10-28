import json
import secrets
import sqlite3
import time
from contextlib import contextmanager
from fastapi import HTTPException

RETENTION = 7 * 86400


class Store:
    def __init__(self, directory):
        self.directory = directory

    @contextmanager
    def connection(self):
        connection = sqlite3.connect(self.directory / "snapmenu.sqlite3", timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            with connection:
                yield connection
        finally:
            connection.close()

    def initialize(self):
        (self.directory / "images").mkdir(parents=True, exist_ok=True)
        with self.connection() as db:
            db.executescript("""
                PRAGMA journal_mode=WAL;
                CREATE TABLE IF NOT EXISTS menus (
                    id TEXT PRIMARY KEY, owner TEXT NOT NULL, fingerprint TEXT NOT NULL,
                    created_at REAL NOT NULL, opened_at REAL NOT NULL DEFAULT 0, payload TEXT NOT NULL);
                CREATE INDEX IF NOT EXISTS menu_owner ON menus(owner, created_at);
                CREATE TABLE IF NOT EXISTS images (
                    menu_id TEXT REFERENCES menus(id) ON DELETE CASCADE, dish_id TEXT,
                    status TEXT NOT NULL, task_id TEXT, error TEXT NOT NULL DEFAULT '',
                    attempts INTEGER NOT NULL DEFAULT 1, created_at REAL NOT NULL, checked_at REAL NOT NULL,
                    PRIMARY KEY(menu_id, dish_id));
                CREATE TABLE IF NOT EXISTS usage (owner TEXT, kind TEXT, created_at REAL);
                CREATE INDEX IF NOT EXISTS usage_time ON usage(kind, created_at);
            """)
            if "opened_at" not in {row[1] for row in db.execute("PRAGMA table_info(menus)")}:
                db.execute("ALTER TABLE menus ADD COLUMN opened_at REAL NOT NULL DEFAULT 0")
            db.execute("UPDATE images SET status='uncertain', error='The picture request was interrupted. Please keep browsing.' WHERE status='starting'")
            db.execute("UPDATE images SET status='uncertain', error='This picture belongs to the previous image service and cannot be resumed.' WHERE status='pending' AND (task_id IS NULL OR substr(task_id,1,5) != 'resp_')")
        self.cleanup()

    def check(self):
        with self.connection() as db:
            db.execute("SELECT 1 FROM menus LIMIT 1")

    def cleanup(self):
        with self.connection() as db:
            expired = db.execute("SELECT id FROM menus WHERE created_at < ?", (time.time() - RETENTION,)).fetchall()
            for row in expired:
                db.execute("DELETE FROM menus WHERE id=?", (row["id"],))
                for path in (self.directory / "images").glob(row["id"] + "-*.webp"):
                    path.unlink(missing_ok=True)
            db.execute("DELETE FROM usage WHERE created_at < ?", (time.time() - 86400,))

    def decode(self, row):
        if not row:
            return None
        menu = json.loads(row["payload"])
        with self.connection() as db:
            images = db.execute("SELECT * FROM images WHERE menu_id=?", (menu["id"],)).fetchall()
        lookup = {image["dish_id"]: self.public_image(image) for image in images}
        for dish in menu["dishes"]:
            dish["image"] = lookup.get(dish["id"])
        return menu

    def get(self, menu_id, owner):
        with self.connection() as db:
            row = db.execute("SELECT * FROM menus WHERE id=? AND owner=? AND created_at>?", (menu_id, owner, time.time() - RETENTION)).fetchone()
        return self.decode(row)

    def latest(self, owner):
        with self.connection() as db:
            row = db.execute("SELECT * FROM menus WHERE owner=? AND created_at>? ORDER BY opened_at DESC, created_at DESC LIMIT 1", (owner, time.time() - RETENTION)).fetchone()
        return self.decode(row)

    def find(self, owner, fingerprint):
        with self.connection() as db:
            row = db.execute("SELECT * FROM menus WHERE owner=? AND fingerprint=? AND created_at>? ORDER BY created_at DESC LIMIT 1", (owner, fingerprint, time.time() - RETENTION)).fetchone()
            if row:
                db.execute("UPDATE menus SET opened_at=? WHERE id=?", (time.time(), row["id"]))
        return self.decode(row)

    def create(self, owner, fingerprint, language, result):
        self.cleanup()
        menu = result.model_dump()
        menu.update(id=secrets.token_hex(16), language=language, created_at=time.time(), demo=False)
        for index, dish in enumerate(menu["dishes"]):
            dish["id"] = str(index + 1)
        with self.connection() as db:
            db.execute("INSERT INTO menus(id,owner,fingerprint,created_at,opened_at,payload) VALUES (?, ?, ?, ?, ?, ?)", (menu["id"], owner, fingerprint, menu["created_at"], time.time(), json.dumps(menu, ensure_ascii=False)))
        return self.get(menu["id"], owner)

    def delete(self, menu_id, owner):
        with self.connection() as db:
            db.execute("DELETE FROM menus WHERE id=? AND owner=?", (menu_id, owner))
        for path in (self.directory / "images").glob(menu_id + "-*.webp"):
            path.unlink(missing_ok=True)

    def consume(self, owner, kind, daily_limit, hourly_limit):
        with self.connection() as db:
            db.execute("BEGIN IMMEDIATE")
            total = db.execute("SELECT count(*) FROM usage WHERE kind=? AND created_at>?", (kind, time.time() - 86400)).fetchone()[0]
            personal = db.execute("SELECT count(*) FROM usage WHERE kind=? AND owner=? AND created_at>?", (kind, owner, time.time() - 3600)).fetchone()[0]
            if total >= daily_limit or personal >= hourly_limit:
                raise HTTPException(429, "The menu service limit has been reached. Please try again later.")
            db.execute("INSERT INTO usage VALUES (?, ?, ?)", (owner, kind, time.time()))

    def public_image(self, row):
        image = dict(row)
        image.pop("task_id", None)
        if image["status"] == "ready":
            image["url"] = f"/api/menus/{image['menu_id']}/dishes/{image['dish_id']}/picture"
        return image

    def image(self, menu_id, dish_id):
        with self.connection() as db:
            row = db.execute("SELECT * FROM images WHERE menu_id=? AND dish_id=?", (menu_id, dish_id)).fetchone()
        return dict(row) if row else None

    def claim_image(self, menu_id, dish_id):
        with self.connection() as db:
            db.execute("""INSERT INTO images(menu_id,dish_id,status,created_at,checked_at) VALUES (?,?,'starting',?,?)
                ON CONFLICT(menu_id,dish_id) DO UPDATE SET status='starting',task_id=NULL,error='',attempts=attempts+1,created_at=excluded.created_at,checked_at=excluded.checked_at""", (menu_id, dish_id, time.time(), time.time()))

    def update_image(self, menu_id, dish_id, **fields):
        assert set(fields) <= {"status", "task_id", "error", "checked_at"}
        with self.connection() as db:
            db.execute("UPDATE images SET " + ",".join(key + "=?" for key in fields) + " WHERE menu_id=? AND dish_id=?", (*fields.values(), menu_id, dish_id))

    def active_images(self):
        with self.connection() as db:
            return db.execute("SELECT count(*) FROM images WHERE status IN ('starting','pending') AND created_at>?", (time.time() - 600,)).fetchone()[0]

    def pending_tasks(self, menu_id):
        with self.connection() as db:
            return [row[0] for row in db.execute("SELECT task_id FROM images WHERE menu_id=? AND status='pending' AND task_id IS NOT NULL", (menu_id,))]

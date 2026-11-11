import { useEffect, useRef, useState } from "react";
import { createRoot } from "react-dom/client";
import { Button } from "@base-ui/react/button";
import { Select } from "@base-ui/react/select";
import { Dialog } from "@base-ui/react/dialog";
import type { Dish, Menu, ImageState } from "../src/models";
import { prepare } from "./upload";
import "./style.css";

type Config = {
  languages: Record<string, string>;
  provider: string;
  reading_available: boolean;
  images_available: boolean;
};
const lifetime = new AbortController();
window.addEventListener("pagehide", () => lifetime.abort());
async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch("/api" + path, {
    ...init,
    signal: lifetime.signal,
  });
  let data: any;
  try {
    data = await response.json();
  } catch {
    throw Error("The connection was interrupted. Please try again.");
  }
  if (!response.ok)
    throw Object.assign(Error(data.detail || "Something went wrong."), {
      status: response.status,
    });
  return data;
}
const post = (body?: unknown): RequestInit => ({
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: body === undefined ? undefined : JSON.stringify(body),
});
function Camera() {
  return (
    <svg
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      aria-hidden="true"
    >
      <path d="M8 5 10 3h4l2 2h4v15H4V5z" />
      <circle cx="12" cy="12" r="4" />
    </svg>
  );
}
function Choice({
  value,
  onChange,
  items,
  label,
}: {
  value: string;
  onChange: (v: string) => void;
  items: Record<string, string>;
  label: string;
}) {
  return (
    <Select.Root
      value={value}
      onValueChange={(v) => v && onChange(v)}
      items={items}
    >
      <Select.Trigger className="select" aria-label={label}>
        <Select.Value />
        <Select.Icon aria-hidden="true">⌄</Select.Icon>
      </Select.Trigger>
      <Select.Portal>
        <Select.Positioner
          sideOffset={6}
          alignItemWithTrigger={false}
          className="positioner"
        >
          <Select.Popup className="select-popup">
            <Select.List>
              {Object.entries(items).map(([v, text]) => (
                <Select.Item className="select-item" key={v} value={v}>
                  <Select.ItemText>{text}</Select.ItemText>
                  <Select.ItemIndicator>✓</Select.ItemIndicator>
                </Select.Item>
              ))}
            </Select.List>
          </Select.Popup>
        </Select.Positioner>
      </Select.Portal>
    </Select.Root>
  );
}
const sample: Menu = {
  id: "sample",
  demo: true,
  title: "Sample menu",
  source_language: "English",
  language: "en",
  created_at: 0,
  warnings: [],
  dishes: [
    ["Hand Tossed Salad", "with ranch or thousand island", "7$ / 6$", "Salads"],
    ["Roast Beef with Mushroom Sauce", "", "7$", "Entrées"],
    ["Loaded Baked Potato", "", "7$", "Entrées"],
    ["Strawberry Cake", "", "7$", "Desserts"],
  ].map(([name, description, price, category], i) => ({
    id: String(i + 1),
    name_original: name,
    name_translated: name,
    description_original: description,
    description_translated: description,
    price,
    category,
    course: "other",
  })),
};
function App() {
  const [config, setConfig] = useState<Config | null>(null),
    [configError, setConfigError] = useState(false),
    [sessionReady, setSessionReady] = useState(false),
    [menu, setMenu] = useState<Menu | null>(null),
    [latest, setLatest] = useState<Menu | null>(null),
    [stage, setStage] = useState<"home" | "preparing" | "reading" | "menu">(
      "home",
    ),
    [language, setLanguage] = useState("en"),
    [error, setError] = useState(""),
    [category, setCategory] = useState("all"),
    [page, setPage] = useState(0),
    [detail, setDetail] = useState<Dish | null>(null),
    [info, setInfo] = useState(false),
    [deleting, setDeleting] = useState(false),
    [short, setShort] = useState(window.innerHeight < 700);
  const camera = useRef<HTMLInputElement>(null),
    upload = useRef<HTMLInputElement>(null),
    attempted = useRef(new Set<string>()),
    active = useRef(new Set<string>()),
    [revision, bump] = useState(0);
  function reset() {
    setStage("home");
    setError("");
    setDetail(null);
  }
  function openMenu(value: Menu) {
    setMenu(value);
    setStage("menu");
    setCategory("all");
    setPage(0);
    setError("");
  }
  useEffect(() => {
    let alive = true;
    api<Config>("/config")
      .then((value) => {
        if (alive) setConfig(value);
      })
      .catch(() => {
        if (alive) setConfigError(true);
      });
    api<{ menu: Menu | null }>("/menus/latest")
      .then((value) => {
        if (alive) setLatest(value.menu);
      })
      .catch(() => {})
      .finally(() => {
        if (alive) setSessionReady(true);
      });
    const resize = () => setShort(window.innerHeight < 700);
    resize();
    window.addEventListener("resize", resize);
    return () => {
      alive = false;
      window.removeEventListener("resize", resize);
    };
  }, []);
  async function scan(file: File | undefined) {
    if (!file) return;
    setError("");
    setStage("preparing");
    try {
      const pages = await prepare(file);
      setStage("reading");
      if (
        new Blob([JSON.stringify({ pages, language })]).size >
        4 * 1024 * 1024
      )
        throw Error(
          "These pages are too large together. Upload one menu page at a time.",
        );
      const result = await api<Menu>("/menus", post({ pages, language }));
      setLatest(result);
      openMenu(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "This menu could not be read.");
      setStage("home");
    } finally {
      if (camera.current) camera.current.value = "";
      if (upload.current) upload.current.value = "";
    }
  }
  function updateImage(menuId: string, dishId: string, image: ImageState) {
    setMenu((current) =>
      current?.id === menuId
        ? {
            ...current,
            dishes: current.dishes.map((d) =>
              d.id === dishId ? { ...d, image } : d,
            ),
          }
        : current,
    );
  }
  const filtered =
      menu?.dishes.filter(
        (d) => category === "all" || d.category === category,
      ) || [],
    size = short ? 2 : 4,
    total = Math.max(1, Math.ceil(filtered.length / size)),
    safePage = Math.min(page, total - 1),
    visible = filtered.slice(safePage * size, (safePage + 1) * size),
    visibleKey = visible.map((d) => d.id).join(",");
  // At most three paid submissions. A persistent server claim prevents duplicate charges across tabs/reloads.
  useEffect(() => {
    if (stage !== "menu" || !menu || menu.demo || !config?.images_available)
      return;
    const currentMenu = menu;
    for (const dish of visible) {
      const token = currentMenu.id + "/" + dish.id;
      if (
        active.current.size +
          currentMenu.dishes.filter(
            (d) => d.image && ["pending", "starting"].includes(d.image.status),
          ).length >=
        3
      )
        break;
      if (dish.image || attempted.current.has(token)) continue;
      attempted.current.add(token);
      active.current.add(token);
      api<ImageState>(
        `/menus/${currentMenu.id}/dishes/${dish.id}/image`,
        post(),
      )
        .then((image) => updateImage(currentMenu.id, dish.id, image))
        .catch((e) => {
          setError(e.message);
          updateImage(currentMenu.id, dish.id, {
            status: "failed",
            attempts: 0,
            error: e.message,
          });
        })
        .finally(() => {
          active.current.delete(token);
          bump((v) => v + 1);
        });
    }
  }, [stage, menu, visibleKey, revision, config?.images_available]);
  useEffect(() => {
    if (stage !== "menu" || !menu || menu.demo) return;
    const pending = menu.dishes.filter(
      (d) => d.image && ["pending", "starting"].includes(d.image.status),
    );
    if (!pending.length) return;
    let stopped = false;
    const menuId = menu.id;
    const poll = async () => {
      if (document.visibilityState === "hidden") return;
      const updates = await Promise.all(
        pending.map(async (dish) => {
          try {
            return {
              id: dish.id,
              image: await api<ImageState>(
                `/menus/${menuId}/dishes/${dish.id}/image`,
              ),
            };
          } catch {
            return null;
          }
        }),
      );
      if (!stopped)
        setMenu((current) =>
          current?.id === menuId
            ? {
                ...current,
                dishes: current.dishes.map((dish) => {
                  const update = updates.find((value) => value?.id === dish.id);
                  return update ? { ...dish, image: update.image } : dish;
                }),
              }
            : current,
        );
    };
    const timer = window.setInterval(poll, 1500);
    return () => {
      stopped = true;
      clearInterval(timer);
    };
  }, [stage, menu, visibleKey]);
  async function retry(dish: Dish) {
    if (!menu) return;
    setError("");
    try {
      const image = await api<ImageState>(
        `/menus/${menu.id}/dishes/${dish.id}/image`,
        post(),
      );
      updateImage(menu.id, dish.id, image);
    } catch (e) {
      setError((e as Error).message);
    }
  }
  async function remove() {
    if (!menu || menu.demo) return;
    setDeleting(true);
    try {
      await api(`/menus/${menu.id}`, { method: "DELETE" });
      setMenu(null);
      setLatest(null);
      reset();
      setInfo(false);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setDeleting(false);
    }
  }
  const categories: Record<string, string> = { all: "All dishes" };
  for (const d of menu?.dishes || []) categories[d.category] = d.category;
  const selected = detail && menu?.dishes.find((d) => d.id === detail.id);
  return (
    <div className="app">
      <header>
        <a
          href="/"
          className="brand"
          onClick={(e) => {
            e.preventDefault();
            reset();
          }}
        >
          SnapMenu
        </a>
        <div className="header-actions">
          {stage === "menu" && (
            <Button className="quiet" onClick={reset}>
              New menu
            </Button>
          )}
          <Button
            className="icon-button"
            onClick={() => setInfo(true)}
            aria-label="About and privacy"
          >
            ⓘ
          </Button>
        </div>
      </header>
      <main>
        {stage === "home" && (
          <section className="home" aria-labelledby="home-title">
            <div className="intro">
              <h1 id="home-title">See what’s on the menu.</h1>
              <p>Take a photo. See the dishes in your language.</p>
            </div>
            <div className="upload-controls">
              <label className="field-label">
                Read in
                <Choice
                  label="Reading language"
                  value={language}
                  onChange={setLanguage}
                  items={config?.languages || { en: "English" }}
                />
              </label>
              <Button
                className="primary capture"
                disabled={!config?.reading_available || !sessionReady}
                onClick={() => camera.current?.click()}
              >
                <Camera />
                Take a photo
              </Button>
              <Button
                className="secondary"
                disabled={!config?.reading_available || !sessionReady}
                onClick={() => upload.current?.click()}
              >
                Upload menu
              </Button>
              <p className="hint">Photo or PDF · Up to 10 MB</p>
            </div>
            <div className="home-footer">
              {error && (
                <p className="error" role="alert">
                  {error}
                </p>
              )}
              {configError && (
                <p className="error" role="alert">
                  Connection unavailable. Reload to try again.
                </p>
              )}
              {config && !config.reading_available && (
                <p className="notice" role="status">
                  AI is not connected yet. You can explore the sample.
                </p>
              )}
              {latest && (
                <Button className="quiet" onClick={() => openMenu(latest)}>
                  Back to your last menu
                </Button>
              )}
              <Button className="quiet" onClick={() => openMenu(sample)}>
                View sample menu
              </Button>
              <p className="fine">
                Dish images are AI estimates, not restaurant photos.
              </p>
            </div>
          </section>
        )}
        {["preparing", "reading"].includes(stage) && (
          <section className="processing" aria-live="polite">
            <div className="spinner" aria-hidden="true" />
            <h1>
              {stage === "preparing" ? "Preparing photo" : "Reading your menu"}
            </h1>
            <p>
              {stage === "preparing"
                ? "Making the upload smaller."
                : "Dishes appear first. Pictures follow."}
            </p>
            <p className="fine">
              Keep this tab open. Large menus can take a minute.
            </p>
          </section>
        )}
        {stage === "menu" && menu && (
          <section className="menu-screen" aria-label="Visual menu">
            <div className="menu-top">
              <div className="title-row">
                <h1>{menu.title}</h1>
                <span className="count">{menu.dishes.length} dishes</span>
              </div>
              <div className="filter-row">
                <Choice
                  label="Menu category"
                  value={category}
                  onChange={(v) => {
                    setCategory(v);
                    setPage(0);
                  }}
                  items={categories}
                />
                <span className="fine">
                  {menu.demo
                    ? "SAMPLE · No AI requests"
                    : "AI images · Actual dishes may vary"}
                </span>
              </div>
            </div>
            <div
              className={"dish-grid " + (short ? "short" : "")}
              aria-live="polite"
            >
              {visible.map((dish) => (
                <article key={dish.id} className="dish-card">
                  <Button
                    className="dish-open"
                    onClick={() => setDetail(dish)}
                    aria-label={`View ${dish.name_translated}`}
                  >
                    <div className="dish-visual">
                      {dish.image?.status === "ready" ? (
                        <img
                          src={dish.image.url}
                          alt={`AI illustration of ${dish.name_translated}`}
                          decoding="async"
                          onError={() =>
                            updateImage(menu.id, dish.id, {
                              status: "failed",
                              attempts: 2,
                              error: "The picture could not be displayed.",
                            })
                          }
                        />
                      ) : (
                        <div className="image-placeholder">
                          <span
                            className={
                              dish.image?.status === "pending" ||
                              dish.image?.status === "starting"
                                ? "pulse"
                                : ""
                            }
                          >
                            {menu.demo
                              ? "Sample dish"
                              : dish.image?.status === "uncertain"
                                ? "Request unconfirmed"
                                : dish.image?.status === "failed"
                                  ? "Picture unavailable"
                                  : config?.images_available
                                    ? "Preparing picture…"
                                    : "Pictures unavailable"}
                          </span>
                        </div>
                      )}
                    </div>
                    <div className="dish-copy">
                      <span className="dish-name">{dish.name_translated}</span>
                      <span className="dish-price">
                        {dish.price || "Price not listed"}
                      </span>
                    </div>
                  </Button>
                </article>
              ))}
            </div>
            <div className="menu-status" role="status">
              {error ? (
                <span className="error">{error}</span>
              ) : menu.warnings.length ? (
                <span>{menu.warnings[0]}</span>
              ) : (
                <span>Tap a dish for its original name and details.</span>
              )}
            </div>
            <nav className="pagination" aria-label="Menu pages">
              <Button
                className="secondary"
                aria-label="Previous dishes"
                disabled={safePage === 0}
                onClick={() => setPage((p) => p - 1)}
              >
                ← Back
              </Button>
              <span>
                {safePage + 1} / {total}
              </span>
              <Button
                className="secondary"
                aria-label="Next dishes"
                disabled={safePage >= total - 1}
                onClick={() => setPage((p) => p + 1)}
              >
                Next →
              </Button>
            </nav>
          </section>
        )}
      </main>
      <input
        ref={camera}
        type="file"
        accept="image/*"
        capture="environment"
        aria-label="Take a photo of the menu"
        hidden
        onChange={(e) => scan(e.target.files?.[0])}
      />
      <input
        ref={upload}
        type="file"
        accept="image/*,application/pdf,.heic,.heif"
        aria-label="Choose a menu file"
        hidden
        onChange={(e) => scan(e.target.files?.[0])}
      />
      <Dialog.Root
        open={!!detail}
        onOpenChange={(open) => !open && setDetail(null)}
      >
        <Dialog.Portal>
          <Dialog.Backdrop className="backdrop" />
          <Dialog.Popup className="dialog dish-dialog">
            <div className="dialog-top">
              <Dialog.Title>{selected?.name_translated}</Dialog.Title>
              <Dialog.Close className="icon-button" aria-label="Close dish">
                ×
              </Dialog.Close>
            </div>
            <Dialog.Description className="fine">
              {selected?.price || "Price not listed"} · {selected?.category}
            </Dialog.Description>
            {selected?.image?.status === "ready" && (
              <img
                className="detail-image"
                src={selected.image.url}
                alt={`AI illustration of ${selected.name_translated}`}
              />
            )}
            <div className="detail-text">
              <p className="original" lang={menu?.source_language}>
                {selected?.name_original}
              </p>
              <p>
                {selected?.description_translated ||
                  "No description printed on the menu."}
              </p>
              {selected?.description_original !==
                selected?.description_translated && (
                <p className="muted">{selected?.description_original}</p>
              )}
            </div>
            {selected?.image?.status === "failed" &&
              selected.image.attempts < 2 && (
                <Button className="secondary" onClick={() => retry(selected)}>
                  Try picture once more
                </Button>
              )}
            <p className="fine">
              AI images are illustrative. Ask the restaurant about ingredients
              and allergies.
            </p>
          </Dialog.Popup>
        </Dialog.Portal>
      </Dialog.Root>
      <Dialog.Root open={info} onOpenChange={setInfo}>
        <Dialog.Portal>
          <Dialog.Backdrop className="backdrop" />
          <Dialog.Popup className="dialog">
            <div className="dialog-top">
              <Dialog.Title>About SnapMenu</Dialog.Title>
              <Dialog.Close
                className="icon-button"
                aria-label="Close information"
              >
                ×
              </Dialog.Close>
            </div>
            <Dialog.Description>
              Turn a text menu into a visual guide before you order.
            </Dialog.Description>
            <div className="detail-text">
              <p>
                Your photo goes to{" "}
                {config?.provider === "muse" ? "Meta" : "OpenAI"} to read the
                menu. Dish names and descriptions go there to generate pictures.
              </p>
              <p>
                Pictures are AI estimates. Prices stay as printed. Ask the
                restaurant about ingredients and allergies.
              </p>
              <p>
                Menus and pictures are private to this browser and expire after
                seven days. Background image requests use provider storage until
                retrieval or expiry cleanup.
              </p>
            </div>
            {menu && !menu.demo && (
              <Button className="danger" disabled={deleting} onClick={remove}>
                {deleting ? "Deleting…" : "Delete this menu"}
              </Button>
            )}
          </Dialog.Popup>
        </Dialog.Portal>
      </Dialog.Root>
    </div>
  );
}
createRoot(document.getElementById("root")!).render(<App />);

const $ = (id) => document.getElementById(id);
const state = { menu: null, savedMenu: null, file: null, preview: null, category: "All dishes", query: "", picksOnly: false, picks: new Set(), dish: null, busy: false, polling: false, config: null };
const sample = {
  id: "sample", title: "Trattoria del Sole", language: "en", source_language: "Italian", demo: true, warnings: [],
  dishes: [
    { id: "1", name_original: "Burrata e pomodori", name_translated: "Burrata & tomatoes", description_original: "Burrata, pomodori di stagione e basilico.", description_translated: "Creamy burrata, seasonal tomatoes, and fresh basil.", price: "€12", category: "Starters", course: "starter" },
    { id: "2", name_original: "Bruschetta al pomodoro", name_translated: "Tomato bruschetta", description_original: "Pane tostato, pomodoro, aglio e olio extravergine.", description_translated: "Toasted bread with tomatoes, garlic, and extra virgin olive oil.", price: "€8", category: "Starters", course: "starter" },
    { id: "3", name_original: "Spaghetti al pomodoro", name_translated: "Spaghetti pomodoro", description_original: "Spaghetti, salsa di pomodoro e basilico fresco.", description_translated: "Spaghetti in a simple tomato sauce, finished with fresh basil.", price: "€16", category: "Mains", course: "main" },
    { id: "4", name_original: "Risotto ai funghi", name_translated: "Mushroom risotto", description_original: "Riso Carnaroli, funghi di stagione e Parmigiano.", description_translated: "Carnaroli rice with seasonal mushrooms and Parmesan.", price: "€19", category: "Mains", course: "main" },
    { id: "5", name_original: "Tiramisù della casa", name_translated: "House tiramisu", description_original: "Savoiardi, caffè, mascarpone e cacao.", description_translated: "Coffee-soaked sponge fingers, mascarpone, and cocoa.", price: "€7", category: "Desserts", course: "dessert" },
    { id: "6", name_original: "Gelato artigianale", name_translated: "Artisan gelato", description_original: "Chiedi i gusti del giorno.", description_translated: "Ask about today’s flavors.", price: "€5", category: "Desserts", course: "dessert" },
  ],
};

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}
function icon(name, className = "") {
  const node = document.createElementNS("http://www.w3.org/2000/svg", "svg");
  node.setAttribute("aria-hidden", "true");
  if (className) node.setAttribute("class", className);
  const use = document.createElementNS("http://www.w3.org/2000/svg", "use");
  use.setAttribute("href", `#icon-${name}`);
  node.append(use);
  return node;
}
async function api(url, options = {}) {
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 105000);
  try {
    const response = await fetch(url, { ...options, signal: controller.signal });
    const body = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(typeof body.detail === "string" ? body.detail : "Something went wrong. Please try again.");
    return body;
  } catch (error) {
    if (error.name === "AbortError") throw new Error("This is taking longer than expected. Refresh to check for a saved menu before trying again.");
    if (error instanceof TypeError) throw new Error("Could not connect. Check your internet connection and try again.");
    throw error;
  } finally { clearTimeout(timeout); }
}
let toastTimer;
function toast(message) {
  $("toast").textContent = message;
  $("toast").hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { $("toast").hidden = true; }, 3500);
}
function notice(id, message) { $(id).textContent = message || ""; $(id).hidden = !message; }
function view(name, push = false) {
  for (const id of ["home", "processing", "menu-view"]) $(id).hidden = id !== name;
  $("new-menu").hidden = name !== "menu-view";
  if (push) history.pushState({ view: name }, "", name === "menu-view" ? "#menu" : location.pathname);
  window.scrollTo({ top: 0, behavior: "instant" });
  $("main").focus({ preventScroll: true });
}
function home(push = true) {
  if (state.busy) return;
  $("resume-menu").hidden = !state.savedMenu;
  view("home", push);
}
window.addEventListener("popstate", () => {
  if (state.busy) return;
  if (location.hash === "#menu" && state.menu) view("menu-view");
  else home(false);
});
$("new-menu").onclick = () => home();
$("scan-own").onclick = () => home();
$("resume-menu").onclick = () => loadMenu(state.savedMenu);
$("take-photo").onclick = () => $("camera-file").click();
$("choose-file").onclick = () => $("upload-file").click();
$("privacy-button").onclick = () => $("privacy-dialog").showModal();
$("close-privacy").onclick = () => $("privacy-dialog").close();
$("close-dish").onclick = () => $("dish-dialog").close();
for (const dialog of [$("dish-dialog"), $("privacy-dialog")]) {
  dialog.addEventListener("click", (event) => {
    const bounds = dialog.getBoundingClientRect();
    if (event.clientX < bounds.left || event.clientX > bounds.right || event.clientY < bounds.top || event.clientY > bounds.bottom) dialog.close();
  });
}

function clearFile() {
  if (state.preview) URL.revokeObjectURL(state.preview);
  state.file = null; state.preview = null;
  $("file-preview").hidden = true;
  $("scan-button").hidden = true;
  $("camera-file").value = ""; $("upload-file").value = "";
  $("take-photo").querySelector("span").textContent = "Take a photo";
  notice("upload-error", "");
}
$("remove-file").onclick = clearFile;
function chooseFile(event) {
  const file = event.target.files[0];
  if (!file) return;
  if (file.size > 10 * 1024 * 1024) { notice("upload-error", "Choose a file smaller than 10 MB."); event.target.value = ""; return; }
  if (state.preview) URL.revokeObjectURL(state.preview);
  state.file = file;
  $("file-name").textContent = file.name;
  $("file-size").textContent = `${(file.size / 1024 / 1024).toFixed(1)} MB · Ready to read`;
  $("file-preview").hidden = false;
  $("preview-image").hidden = true;
  if (file.type.startsWith("image/") && !/hei[cf]/i.test(file.type)) {
    state.preview = URL.createObjectURL(file);
    $("preview-image").src = state.preview;
    $("preview-image").hidden = false;
    $("preview-image").onerror = () => { $("preview-image").hidden = true; };
  }
  $("take-photo").querySelector("span").textContent = "Retake photo";
  $("scan-button").hidden = false;
  notice("upload-error", "");
  $("scan-button").focus();
}
$("camera-file").onchange = chooseFile;
$("upload-file").onchange = chooseFile;
$("scan-form").onsubmit = async (event) => {
  event.preventDefault();
  if (state.busy || !state.file) return;
  state.busy = true;
  view("processing");
  notice("upload-error", "");
  const form = new FormData();
  form.append("file", state.file);
  const slow = setTimeout(() => { $("progress-copy").textContent = "Still reading. Larger menus can take a minute."; }, 25000);
  try {
    await startup;
    const menu = await api(`/api/menus?language=${encodeURIComponent($("language").value)}`, { method: "POST", body: form });
    loadMenu(menu);
    clearFile();
  } catch (error) {
    view("home");
    notice("upload-error", error.message);
    $("upload-error").scrollIntoView({ block: "nearest" });
  } finally {
    state.busy = false;
    clearTimeout(slow);
    $("progress-copy").textContent = "Reading the dishes and translating your menu…";
  }
};
$("try-sample").onclick = () => loadMenu(structuredClone(sample));

function loadMenu(menu, push = true) {
  if (!menu.demo) state.savedMenu = menu;
  state.menu = menu; state.query = ""; state.category = "All dishes"; state.picksOnly = false;
  try { state.picks = new Set(JSON.parse(localStorage.getItem(`snapmenu-picks-${menu.id}`) || "[]")); } catch { state.picks = new Set(); }
  state.picks = new Set([...state.picks].filter(id => menu.dishes.some(dish => dish.id === id)));
  $("search").value = "";
  $("suggestion").hidden = true;
  $("menu-title").textContent = menu.title;
  $("menu-title").dir = "auto";
  const language = $("language").querySelector(`option[value="${menu.language}"]`)?.textContent || "English";
  $("menu-meta").textContent = `Reading language: ${language}`;
  $("menu-summary").textContent = `${menu.dishes.length} dishes${menu.source_language ? ` · Original: ${menu.source_language}` : ""}`;
  $("demo-notice").hidden = !menu.demo;
  $("delete-menu").hidden = menu.demo;
  notice("menu-warnings", menu.warnings.join(" "));
  renderCategories(); renderDishes();
  view("menu-view", push);
}
function renderCategories() {
  const categories = ["All dishes", ...new Set(state.menu.dishes.map(dish => dish.category))];
  $("categories").replaceChildren(...categories.map(category => {
    const button = element("button", "", category);
    button.setAttribute("aria-pressed", String(category === state.category));
    button.dir = "auto";
    button.onclick = () => {
      state.category = category;
      renderCategories(); renderDishes();
      [...$("categories").children].find(node => node.textContent === category)?.focus({ preventScroll: true });
    };
    return button;
  }));
}
function placeholder(className) {
  const node = element("div", `${className} dish-placeholder`);
  node.textContent = "Image unavailable";
  node.setAttribute("aria-hidden", "true");
  return node;
}
function renderDishes() {
  const query = state.query.toLocaleLowerCase();
  const dishes = state.menu.dishes.filter(dish =>
    (state.category === "All dishes" || dish.category === state.category) &&
    (!state.picksOnly || state.picks.has(dish.id)) &&
    [dish.name_original, dish.name_translated, dish.description_original, dish.description_translated].join(" ").toLocaleLowerCase().includes(query));
  const groups = new Map();
  for (const dish of dishes) {
    if (!groups.has(dish.category)) groups.set(dish.category, []);
    groups.get(dish.category).push(dish);
  }
  const sections = [];
  for (const [category, items] of groups) {
    const section = element("section", "dish-section");
    const heading = element("div", "section-heading");
    const h2 = element("h2", "", category); h2.dir = "auto";
    heading.append(h2, element("span", "", String(items.length)));
    const grid = element("div", "dish-grid");
    for (const dish of items) grid.append(dishCard(dish));
    section.append(heading, grid); sections.push(section);
  }
  $("dishes").replaceChildren(...sections);
  $("empty-results").hidden = dishes.length !== 0;
  $("pick-count").textContent = state.picks.size;
  $("shortlist-toggle").setAttribute("aria-pressed", String(state.picksOnly));
}
function dishCard(dish) {
  const article = element("article", "dish-card");
  const open = element("button", "dish-open");
  open.setAttribute("aria-label", `View ${dish.name_translated}`);
  const photoWrap = element("div");
  if (dish.image?.url) {
    const image = element("img", "dish-thumbnail");
    image.src = dish.image.url; image.alt = ""; image.loading = "lazy";
    image.onerror = () => image.replaceWith(placeholder("dish-thumbnail"));
    photoWrap.append(image, element("p", "image-label", "AI interpretation"));
  }
  const text = element("div", "dish-text");
  const title = element("h3", "", dish.name_translated); title.dir = "auto";
  text.append(title);
  if (dish.name_original !== dish.name_translated) { const original = element("p", "original", dish.name_original); original.dir = "auto"; text.append(original); }
  const description = element("p", "description", dish.description_translated); description.dir = "auto";
  const price = element("p", "price", dish.price || "Price not shown"); price.dir = "auto";
  text.append(description, price);
  if (dish.image?.url) open.append(photoWrap);
  open.append(text); open.onclick = () => openDish(dish.id);
  const pick = element("button", "pick-button"); pick.dataset.dishPick = dish.id;
  pick.setAttribute("aria-label", `${state.picks.has(dish.id) ? "Remove" : "Save"} ${dish.name_translated}${state.picks.has(dish.id) ? " from" : " to"} my picks`);
  pick.setAttribute("aria-pressed", String(state.picks.has(dish.id))); pick.append(icon("heart"));
  pick.onclick = () => { togglePick(dish.id); document.querySelector(`[data-dish-pick="${dish.id}"]`)?.focus({ preventScroll: true }); };
  article.append(open, pick); return article;
}
$("search").oninput = (event) => { state.query = event.target.value.trim(); renderDishes(); };
$("shortlist-toggle").onclick = () => { state.picksOnly = !state.picksOnly; renderDishes(); };
$("reset-filters").onclick = () => {
  state.query = ""; state.category = "All dishes"; state.picksOnly = false; $("search").value = ""; renderCategories(); renderDishes();
};
function togglePick(id) {
  if (state.picks.has(id)) state.picks.delete(id); else state.picks.add(id);
  try { localStorage.setItem(`snapmenu-picks-${state.menu.id}`, JSON.stringify([...state.picks])); } catch { toast("Your browser cannot save picks after this visit."); }
  renderDishes(); updatePickButton();
}
function updatePickButton() {
  if (!state.dish) return;
  const picked = state.picks.has(state.dish.id);
  $("detail-pick").querySelector("span").textContent = picked ? "Remove from my picks" : "Add to my picks";
  $("detail-pick").setAttribute("aria-pressed", String(picked));
}
$("detail-pick").onclick = () => togglePick(state.dish.id);
function openDish(id) {
  const dish = state.menu.dishes.find(item => item.id === id);
  state.dish = dish;
  $("dish-category").textContent = dish.category;
  $("dish-title").textContent = dish.name_translated;
  $("dish-price").textContent = dish.price || "Price not shown";
  $("dish-description").textContent = dish.description_translated || "No description on the menu. Ask the restaurant for details.";
  $("original-text").hidden = dish.name_translated === dish.name_original && dish.description_translated === dish.description_original;
  $("original-name").textContent = dish.name_original;
  $("original-description").textContent = dish.description_original;
  updateDishImage(); updatePickButton();
  if (!$("dish-dialog").open) $("dish-dialog").showModal();
}
function updateDishImage() {
  const image = state.dish.image;
  const picture = $("dish-picture");
  picture.replaceChildren();
  picture.hidden = !image?.url && !["pending", "starting"].includes(image?.status);
  if (image?.url) {
    const photo = element("img"); photo.src = image.url; photo.alt = `AI interpretation of ${state.dish.name_translated}`;
    photo.onerror = () => { picture.hidden = true; notice("image-error", "This picture could not be displayed. Refresh to try loading it again."); };
    picture.append(photo, element("span", "picture-badge", "AI INTERPRETATION"));
  } else {
    picture.append(element("span", "picture-status", "Generating image…"));
  }
  const button = $("generate-image");
  button.hidden = state.menu.demo || image?.status === "ready" || image?.status === "uncertain" || (image?.status === "failed" && image.attempts >= 2);
  button.disabled = image?.status === "pending" || image?.status === "starting";
  button.querySelector("span").textContent = button.disabled ? "Generating image…" : image?.status === "failed" ? "Retry image" : "Generate image";
  notice("image-error", image?.error || (!state.menu.demo && !state.config?.images_available ? "Dish pictures are not connected yet. You can still read every dish." : ""));
  if (!state.config?.images_available && !state.menu.demo) button.hidden = true;
}
$("generate-image").onclick = async () => {
  const menu = state.menu, dish = state.dish;
  $("generate-image").disabled = true;
  try {
    dish.image = await api(`/api/menus/${menu.id}/dishes/${dish.id}/image`, { method: "POST" });
    if (state.menu === menu && state.dish === dish) updateDishImage();
  } catch (error) { notice("image-error", error.message); $("generate-image").disabled = false; }
};
setInterval(async () => {
  if (!state.menu || state.menu.demo || state.polling || document.hidden) return;
  const menu = state.menu;
  const pending = menu.dishes.filter(dish => dish.image?.status === "pending" || dish.image?.status === "starting");
  if (!pending.length) return;
  state.polling = true;
  try {
    for (const dish of pending) {
      if (state.menu !== menu) break;
      try {
        const result = await api(`/api/menus/${menu.id}/dishes/${dish.id}/image`);
        const previous = dish.image.status;
        dish.image = result;
        if (state.dish === dish && $("dish-dialog").open) updateDishImage();
        if (previous !== result.status) { renderDishes(); if (result.status === "ready") toast(`${dish.name_translated}: picture ready`); }
      } catch (error) {
        if (state.dish === dish && $("dish-dialog").open) notice("image-error", error.message);
      }
    }
  } finally { state.polling = false; }
}, 5500);

$("suggest").onclick = () => {
  const courses = ["starter", "main", "dessert"];
  let selections = courses.flatMap(course => {
    const choices = state.menu.dishes.filter(dish => dish.course === course);
    return choices.length ? [choices[Math.floor(Math.random() * choices.length)]] : [];
  });
  if (!selections.length) selections = [state.menu.dishes[Math.floor(Math.random() * state.menu.dishes.length)]];
  $("suggested-dishes").replaceChildren(...selections.map(dish => {
    const button = element("button", "suggested-dish");
    button.append(element("span", "", dish.name_translated), element("span", "", dish.price || "Price not shown"));
    button.onclick = () => openDish(dish.id);
    return button;
  }));
  $("suggestion").hidden = false;
  $("suggestion").scrollIntoView({ block: "nearest", behavior: "smooth" });
};
$("dismiss-suggestion").onclick = () => { $("suggestion").hidden = true; $("suggest").focus(); };
$("delete-menu").onclick = async () => {
  if (!confirm("Delete this menu and its dish pictures from SnapMenu?")) return;
  const button = $("delete-menu"); button.disabled = true;
  try {
    await api(`/api/menus/${state.menu.id}`, { method: "DELETE" });
    try { localStorage.removeItem(`snapmenu-picks-${state.menu.id}`); } catch {}
    state.menu = null; state.savedMenu = null; state.dish = null;
    clearFile(); home(); toast("Your menu has been deleted.");
  } catch (error) { toast(error.message); } finally { button.disabled = false; }
};

async function start() {
  try {
    // Establish the private session cookie before any simultaneous API calls.
    state.config = await api("/api/config");
    if (!state.config.reading_available) notice("service-notice", "Menu reading is not set up. You can view a sample menu.");
    const { menu } = await api("/api/menus/latest");
    if (menu) {
      state.savedMenu = menu;
      if (!state.menu && !state.busy) loadMenu(menu, false);
    }
  } catch (error) { notice("upload-error", error.message); }
}
const startup = start();

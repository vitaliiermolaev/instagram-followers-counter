// Instagram Followers Counter: the follower count of a public Instagram profile.
//
// The count comes from the profile page itself: its <head> has a meta tag like
// content="104M Followers, 95 Following, 5,017 Posts - See Instagram photos and videos from NASA (&#064;nasa)".
// The page is large, so it is read as a stream and only the start is searched.

const APP_ID = "io.github.vitaliiermolaev.insta";
const DRAW = "http://localhost/api/display/draw";
const SETTINGS = "http://localhost/api/apps/settings?app_id=" + APP_ID;

const REFRESH_MS = 15 * 60 * 1000;
const RETRY_MS = 5 * 60 * 1000;
const SETTINGS_POLL_MS = 10 * 1000;
const MAX_PAGE_BYTES = 4 * 1024 * 1024;
// With a browser User-Agent (the firmware default) Instagram returns an empty app shell
// without the profile data, so the app names itself.
const USER_AGENT = "BUSY-Bar-Instagram-Followers-Counter/1.0";
const TAIL_CHARS = 1000;
const SCROLL_PX_PER_MIN = 900;

const WHITE = "#FFFFFFFF";
const GRAY = "#9AA0A6FF";

const TEXT_X = 18;
const TEXT_WIDTH = 53;

const COUNT_PATTERN = /content="([0-9][0-9.,]*[KMB]?) Followers?, [^"]{0,300}"/;
const USER_PATTERN = /\((?:@|&#0*64;|&#x0*40;)([A-Za-z0-9._]{1,30})\)/i;

const PINK = "#F280D7FF"; // middle of the label gradient in the design

// Explicit layers: without z_index the firmware numbers elements by their place in each request,
// and the animation, sent once, would end up level with the text and could cover it.
const Z_BACKGROUND = 0;
const Z_ANIMATION = 10;
const Z_TEXT = 20;
const Z_BADGE = 30;

// Background with the Instagram icon, from the Figma design.
const BACKGROUND = { id: "bg", type: "image", path: "images/bg.png", x: 0, y: 0, z_index: Z_BACKGROUND };

// Hearts floating up in the bottom-right corner, next to the count (tools/hearts.py).
const HEARTS = {
  id: "hearts",
  type: "animation",
  path: "animations/hearts.anim",
  loop: true,
  x: 54,
  y: 0,
  z_index: Z_ANIMATION,
};

// Red cross in the bottom-right corner of the logo: the last update failed.
const BADGE = {
  id: "badge",
  type: "xpmbitmap",
  x: 11,
  y: 11,
  z_index: Z_BADGE,
  data: "! XPM2\n5 5 2 1\nk c #000000\nr c #FF3B30\nkkkkk\nkrkrk\nkkrkk\nkrkrk\nkkkkk",
};

let profile = null; // username from the settings, "" when none is set
let user = ""; // username as Instagram spells it
let count = ""; // "104M", "19.8K", "5,017"
let message = ""; // status shown instead of the count
let failed = false;
let refreshing = false;
let running = true;
let refreshTimer = null;
let settingsTimer = null;
let shownKey = "";
let badgeShown = false;
let heartsShown = false;

function draw(elements) {
  return fetch(DRAW, {
    method: "POST",
    body: JSON.stringify({ application_name: APP_ID, elements: elements }),
  });
}

function remove(ids) {
  return fetch(DRAW, {
    method: "DELETE",
    body: JSON.stringify({ application_name: APP_ID, element_ids: ids }),
  });
}

function text(id, y, value, font, color) {
  return {
    id: id,
    type: "text",
    z_index: Z_TEXT,
    x: TEXT_X,
    y: y,
    text: value,
    font: font,
    color: color,
    width: TEXT_WIDTH,
    scroll_rate: SCROLL_PX_PER_MIN,
    scroll_start_delay: 2000,
    scroll_repeat_delay: 3000,
  };
}

async function render() {
  let top;
  let bottom;
  if (profile === "") {
    top = text("top", 0, "Add profile", "small", PINK);
    bottom = text("bottom", 8, "in settings", "small", WHITE);
  } else {
    // Caps read better in the small font at a glance; usernames are case-insensitive anyway.
    top = text("top", 0, (user || profile).toUpperCase(), "small", PINK);
    if (count !== "") bottom = text("bottom", 6, count, "bold", WHITE);
    else if (message !== "") bottom = text("bottom", 8, message, "small", GRAY);
    else bottom = text("bottom", 6, "--", "bold", WHITE);
  }
  const hasCount = profile !== "" && count !== "";
  const badge = hasCount && failed;
  const key = JSON.stringify([top.text, top.font, bottom.text, bottom.font, badge]);
  if (key === shownKey) return;
  shownKey = key;

  const elements = [BACKGROUND];
  if (hasCount && !heartsShown) elements.push(HEARTS); // sent once, so the loop doesn't restart
  elements.push(top, bottom);
  if (badge) elements.push(BADGE);
  await draw(elements);
  const gone = [];
  if (!badge && badgeShown) gone.push("badge");
  if (!hasCount && heartsShown) gone.push("hearts");
  if (gone.length > 0) await remove(gone);
  badgeShown = badge;
  heartsShown = hasCount;
}

// "https://www.instagram.com/nasa/?hl=en", "instagram.com/nasa", "@nasa", "nasa" -> "nasa"
function parseProfile(value) {
  let name = String(value || "").trim();
  const link = name.match(/instagram\.com\/([^/?#\s]+)/i);
  if (link) name = link[1];
  name = name.replace(/^@/, "").toLowerCase();
  return /^[a-z0-9._]{1,30}$/.test(name) ? name : "";
}

async function readProfile() {
  const response = await fetch(SETTINGS);
  if (response.status !== 200) throw new Error("settings " + response.status);
  const doc = JSON.parse(await response.text());
  return parseProfile(doc.values && doc.values.profile);
}

function bytesToText(bytes) {
  let result = "";
  for (let i = 0; i < bytes.length; i += 1024) {
    result += String.fromCharCode.apply(null, bytes.subarray(i, i + 1024));
  }
  return result;
}

// Streams the page and returns the content of the followers meta tag, or "".
// The body is read to the end: on firmware 1.4 an abandoned body keeps downloading
// into memory, so the rest of the page is read and dropped chunk by chunk.
async function readFollowersTag(response) {
  const reader = response.body.getReader();
  let found = "";
  let tail = "";
  let total = 0;
  for (;;) {
    const step = await reader.read();
    if (step.done) break;
    const chunk = step.value;
    total += chunk.length;
    if (found === "") {
      const text = tail + bytesToText(chunk);
      const match = COUNT_PATTERN.exec(text);
      if (match) found = match[0];
      else tail = text.slice(-TAIL_CHARS);
    }
    if (total > MAX_PAGE_BYTES) {
      await reader.cancel();
      break;
    }
  }
  console.log("page bytes:", total, "found:", found !== "");
  return found;
}

async function fetchFollowers(name) {
  const response = await fetch("https://www.instagram.com/" + name + "/", {
    headers: { "User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.9" },
  });
  if (response.status === 404) return { error: "Not found" };
  if (response.status !== 200) {
    console.log("instagram status:", response.status);
    return { error: "Can't load" };
  }
  const tag = await readFollowersTag(response);
  // A missing profile comes back as 200 with an empty app shell, same as a blocked request.
  // Without a count shown yet, a typo in the username is the likely reason.
  if (tag === "") return { error: "Not found" };
  const spelled = tag.match(USER_PATTERN);
  return {
    count: COUNT_PATTERN.exec(tag)[1],
    user: spelled && spelled[1].toLowerCase() === name ? spelled[1] : name,
  };
}

function saveCache() {
  try {
    localStorage.setItem("last", JSON.stringify({ profile: profile, user: user, count: count }));
  } catch (error) {
    console.log("cache save failed:", error);
  }
}

function loadCache() {
  try {
    const last = JSON.parse(localStorage.getItem("last") || "null");
    if (last && last.profile === profile) {
      user = last.user || "";
      count = last.count || "";
    }
  } catch (error) {
    console.log("cache load failed:", error);
  }
}

function scheduleRefresh(ms) {
  if (refreshTimer !== null) clearTimeout(refreshTimer);
  refreshTimer = running ? setTimeout(refresh, ms) : null;
}

async function refresh() {
  refreshTimer = null;
  if (!running || refreshing || profile === "") return;
  refreshing = true;
  const name = profile;
  let result;
  try {
    result = await fetchFollowers(name);
  } catch (error) {
    console.log("refresh failed:", error);
    result = { error: "No connection" };
  }
  refreshing = false;
  if (name !== profile) {
    // The settings changed while loading: start over with the new profile.
    scheduleRefresh(0);
    return;
  }
  let wait = REFRESH_MS;
  if (result.error) {
    failed = true;
    message = result.error;
    wait = RETRY_MS;
  } else {
    failed = false;
    message = "";
    user = result.user;
    count = result.count;
    saveCache();
  }
  await render();
  scheduleRefresh(wait);
}

async function checkSettings() {
  settingsTimer = null;
  try {
    const next = await readProfile();
    if (next !== profile) {
      profile = next;
      user = "";
      count = "";
      message = "";
      failed = false;
      loadCache();
      await render();
      if (profile !== "") {
        scheduleRefresh(0);
      } else if (refreshTimer !== null) {
        clearTimeout(refreshTimer);
        refreshTimer = null;
      }
    }
  } catch (error) {
    console.log("settings read failed:", error);
  }
  if (running) settingsTimer = setTimeout(checkSettings, SETTINGS_POLL_MS);
}

function stop() {
  running = false;
  if (refreshTimer !== null) clearTimeout(refreshTimer);
  if (settingsTimer !== null) clearTimeout(settingsTimer);
  unbind();
}

const unbind = listen("input", (event) => {
  if (event.key === "back" && event.action === "short") stop();
});

checkSettings();

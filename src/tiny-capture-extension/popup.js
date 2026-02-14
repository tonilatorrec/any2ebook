/* default settings */

const DEFAULT_SETTINGS = {
  autoExportEnabled: false,
  autoExportSubdir: "any2ebook/inbox"
};

/* helper functions */

async function getActiveTab() {
  const tabs = await browser.tabs.query({ active: true, currentWindow: true });
  return tabs && tabs.length ? tabs[0] : null;
}

function nowStampForFilename() {
  // e.g. 2026-02-12T15-30-00Z (filename-safe)
  return new Date().toISOString().replace(/[:]/g, "-");
}

async function getQueue() {
  const result = await browser.storage.local.get({ queue: [] });
  return result.queue;
}

async function setQueue(queue) {
  await browser.storage.local.set({ queue });
}

async function getSettings() {
  const result = await browser.storage.local.get(DEFAULT_SETTINGS);
  return {
    autoExportEnabled: Boolean(result.autoExportEnabled),
    autoExportSubdir: sanitizeSubdir(result.autoExportSubdir)
  };
}

async function setSettings(settingsPatch) {
  const current = await getSettings();
  const next = { ...current, ...settingsPatch }; // upsert settingsPatch to current
  next.autoExportSubdir = sanitizeSubdir(next.autoExportSubdir);
  await browser.storage.local.set(next);
}

async function updateCount() {
  const queue = await getQueue();
  document.getElementById("count").textContent = String(queue.length);
  return queue.length;
}

function setStatus(msg) {
  /**
   * Update the status in the popup window (by default it's hidden).
   */
  document.getElementById("status").textContent = msg;
}

function sanitizeSubdir(rawValue) {
  const normalized = String(rawValue || "")
    .trim()
    .replace(/\\/g, "/")
    .replace(/^\/+|\/+$/g, "");
  return normalized || DEFAULT_SETTINGS.autoExportSubdir;
}

function randomSuffix() {
  return Math.random().toString(36).slice(2, 8);
}

async function autoExportItem(item, settings) {
  const filename = `${sanitizeSubdir(settings.autoExportSubdir)}/aku_capture_item_${nowStampForFilename()}_${randomSuffix()}.json`;
  const json = JSON.stringify([item], null, 2);
  const blob = new Blob([json], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  try {
    await browser.downloads.download({
      url,
      filename,
      saveAs: false,
      conflictAction: "uniquify"
    });
  } finally {
    setTimeout(() => URL.revokeObjectURL(url), 5000);
  }
}

/* functions for events */

async function saveCurrentTab() {
  /**
   * Saves the current tab, add the item to the local queue and updates the counter.
   */
  const settings = await getSettings();
  const tab = await getActiveTab();
  if (!tab || !tab.url) return; // no tabs

  // ignore internal browser pages
  const url = tab.url;
  if (url.startsWith("about:") || url.startsWith("chrome:") || url.startsWith("moz-extension:")) {
    setStatus("Cannot save internal browser pages.");
    return;
  }

  // add the item to queue
  const queue = await getQueue();
  const item = {
    captured_at: new Date().toISOString(),
    source: "browser_extension",
    payload_type: "url",
    payload_ref: url
  };
  queue.push(item);
  await setQueue(queue);

  // auto export if set in the options
  if (settings.autoExportEnabled) {
    try {
      await autoExportItem(item, settings);
      setStatus("Saved + auto-exported ✓");
    } catch (e) {
      console.error(e);
      setStatus("Saved, auto-export failed.");
    }
  } else {
    setStatus("Saved ✓");
  }

  // update (increment) the counter
  await updateCount();
}

async function exportJson() {
  /**
   * Opens the export page, which will export the json file automatically 
   */
  const url = browser.runtime.getURL("export.html");
  await browser.tabs.create({ url });
  setStatus("Export tab opened ✓");
}


async function clearQueue() {
  await setQueue([]);
  await updateCount();
  setStatus("Cleared ✓");
}

async function loadSettingsUi() {
  const settings = await getSettings();
  document.getElementById("autoExportEnabled").checked = settings.autoExportEnabled;
  document.getElementById("autoExportSubdir").value = settings.autoExportSubdir;
}

async function onAutoExportEnabledChange(event) {
  /**
   * change autoExportEnabled whenever the chechbox is clicked (either to set or unset it) 
   */
  await setSettings({ autoExportEnabled: event.target.checked });
  setStatus(event.target.checked ? "Auto-export enabled." : "Auto-export disabled.");
}

async function onAutoExportSubdirChange(event) {
  /**
   * change autoExportSubdir whenever the downloads subfolder is changed 
   */
  const cleanSubdir = sanitizeSubdir(event.target.value);
  event.target.value = cleanSubdir;
  await setSettings({ autoExportSubdir: cleanSubdir });
  setStatus("Auto-export folder saved.");
}

document.getElementById("save").addEventListener("click", () => saveCurrentTab().catch(console.error));
document.getElementById("export").addEventListener("click", () => exportJson().catch(console.error));
document.getElementById("clear").addEventListener("click", () => clearQueue().catch(console.error));
document.getElementById("autoExportEnabled").addEventListener("change", (event) => onAutoExportEnabledChange(event).catch(console.error));
document.getElementById("autoExportSubdir").addEventListener("change", (event) => onAutoExportSubdirChange(event).catch(console.error));

updateCount().catch(console.error);
loadSettingsUi().catch(console.error);

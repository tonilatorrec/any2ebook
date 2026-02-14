const DEFAULT_SETTINGS = {
  autoExportEnabled: false,
  autoExportSubdir: "any2ebook/inbox"
};

async function getActiveTab() {
  const tabs = await browser.tabs.query({ active: true, currentWindow: true });
  return tabs && tabs.length ? tabs[0] : null;
}

function nowISO() {
  return new Date().toISOString();
}

async function loadQueue() {
  const { queue } = await browser.storage.local.get({ queue: [] });
  return queue;
}

async function saveQueue(queue) {
  await browser.storage.local.set({ queue });
  console.log("Queue length now:", queue.length);
}

async function getSettings() {
  const result = await browser.storage.local.get(DEFAULT_SETTINGS);
  return {
    autoExportEnabled: Boolean(result.autoExportEnabled),
    autoExportSubdir: sanitizeSubdir(result.autoExportSubdir)
  };
}

function sanitizeSubdir(rawValue) {
  const normalized = String(rawValue || "")
    .trim()
    .replace(/\\/g, "/")
    .replace(/^\/+|\/+$/g, "");
  return normalized || DEFAULT_SETTINGS.autoExportSubdir;
}

function nowStampForFilename() {
  return new Date().toISOString().replace(/[:]/g, "-");
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

function normalizeUrl(url) {
  // Keep it simple initially: store as-is.
  // Later you can add canonicalization (strip UTM, etc.)
  return url;
}

async function saveCurrentTabUrl() {
  const tab = await getActiveTab();
  if (!tab || !tab.url) return;

  const url = normalizeUrl(tab.url);

  // Avoid saving internal browser pages
  if (url.startsWith("about:") || url.startsWith("chrome:") || url.startsWith("moz-extension:")) {
    return;
  }

  const queue = await loadQueue();
  const item = {
    captured_at: nowISO(),
    source: "browser_extension",
    payload_type: "url",
    payload_ref: url
  };
  queue.push(item);

  await saveQueue(queue);
  const settings = await getSettings();
  if (settings.autoExportEnabled) {
    await autoExportItem(item, settings);
  }
}

// Click on extension icon saves URL
browser.browserAction.onClicked.addListener(() => {
  saveCurrentTabUrl().catch(console.error);
});

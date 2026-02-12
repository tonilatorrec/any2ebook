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
  queue.push({
    captured_at: nowISO(),
    source: "browser_extension",
    payload_type: "url",
    payload_ref: url
  });

  await saveQueue(queue);
}

// Click on extension icon saves URL
browser.browserAction.onClicked.addListener(() => {
  saveCurrentTabUrl().catch(console.error);
});

// Hotkey saves URL
browser.commands.onCommand.addListener((command) => {
  if (command === "save-current-tab") {
    saveCurrentTabUrl().catch(console.error);
  }
});

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

async function updateCount() {
  const queue = await getQueue();
  document.getElementById("count").textContent = String(queue.length);
  return queue.length;
}

function setStatus(msg) {
  document.getElementById("status").textContent = msg;
}

async function saveCurrentTab() {
  console.log("SAVE fired");
  const tabs = await browser.tabs.query({ active: true, currentWindow: true });
  const tab = tabs && tabs.length ? tabs[0] : null;
  if (!tab || !tab.url) return;

  const url = tab.url;
  if (url.startsWith("about:") || url.startsWith("chrome:") || url.startsWith("moz-extension:")) {
    setStatus("Cannot save internal browser pages.");
    return;
  }

  const queue = await getQueue();
  queue.push({
    captured_at: new Date().toISOString(),
    source: "browser_extension",
    payload_type: "url",
    payload_ref: url
  });
  await setQueue(queue);

  await updateCount();
  setStatus("Saved ✓");
}

async function exportJson() {
  const url = browser.runtime.getURL("export.html");
  await browser.tabs.create({ url });
  setStatus("Export tab opened ✓");
}


async function clearQueue() {
  await setQueue([]);
  await updateCount();
  setStatus("Cleared ✓");
}

document.getElementById("save").addEventListener("click", () => saveCurrentTab().catch(console.error));
document.getElementById("export").addEventListener("click", () => exportJson().catch(console.error));
document.getElementById("clear").addEventListener("click", () => clearQueue().catch(console.error));

updateCount().catch(console.error);

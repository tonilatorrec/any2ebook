function nowStampForFilename() {
  return new Date().toISOString().replace(/[:]/g, "-");
}

(async () => {
  const { queue } = await browser.storage.local.get({ queue: [] });
  const json = JSON.stringify(queue, null, 2);

  const blob = new Blob([json], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const filename = `aku_capture_queue_${nowStampForFilename()}.json`;

  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();

  // Cleanup a bit later so the download has time to start
  setTimeout(() => URL.revokeObjectURL(url), 5000);
})();

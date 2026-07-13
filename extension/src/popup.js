async function init() {
  const settings = await getSettings();
  const configured = settings.tandoorHost && settings.tandoorToken && settings.backendUrl;
  document.getElementById("configured").style.display = configured ? "block" : "none";
  document.getElementById("unconfigured").style.display = configured ? "none" : "block";

  for (const id of ["openOptions", "openOptions2"]) {
    const el = document.getElementById(id);
    if (el) el.addEventListener("click", () => chrome.runtime.openOptionsPage());
  }

  if (!configured) return;

  document.getElementById("downloadAll").addEventListener("click", async () => {
    const button = document.getElementById("downloadAll");
    const status = document.getElementById("status");
    button.disabled = true;
    status.textContent = "Erzeuge Sammel-PDF … das kann bei vielen Rezepten mehrere Minuten dauern.";
    try {
      const blob = await requestAllRecipesPdf(settings.backendUrl, settings.tandoorHost, settings.tandoorToken);
      triggerBlobDownload(blob, "Rezeptsammlung.pdf");
      status.textContent = "Fertig!";
    } catch (err) {
      console.error("Tandoor2xcookybooky:", err);
      status.textContent = `Fehler: ${err.message}`;
    } finally {
      button.disabled = false;
    }
  });
}

init();

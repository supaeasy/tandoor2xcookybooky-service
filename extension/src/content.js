// Injected (dynamically registered, see options.js) on the configured Tandoor
// instance's /recipe/* pages. Adds a "Als PDF herunterladen" button near the
// recipe keywords.

(function () {
  const RECIPE_ID_MATCH = window.location.pathname.match(/\/recipe\/(\d+)/);
  if (!RECIPE_ID_MATCH) return;
  const recipeId = RECIPE_ID_MATCH[1];

  if (document.getElementById("tandoor2pdf-button")) return;

  function buildButton() {
    const wrapper = document.createElement("div");
    wrapper.id = "tandoor2pdf-wrapper";
    wrapper.style.margin = "8px 0";

    const button = document.createElement("button");
    button.id = "tandoor2pdf-button";
    button.type = "button";
    button.textContent = "📄 Als PDF herunterladen (xcookybooky)";
    button.style.cssText =
      "padding:6px 14px;border-radius:6px;border:1px solid #888;background:#fff;cursor:pointer;font-size:0.9em;";

    const status = document.createElement("span");
    status.id = "tandoor2pdf-status";
    status.style.marginLeft = "10px";
    status.style.fontSize = "0.85em";

    button.addEventListener("click", async () => {
      button.disabled = true;
      status.textContent = "Erzeuge PDF … (kann etwas dauern)";
      try {
        const settings = await getSettings();
        if (!settings.tandoorHost || !settings.tandoorToken || !settings.backendUrl) {
          throw new Error("Bitte zuerst die Einstellungen der Erweiterung ausfüllen.");
        }
        const blob = await requestRecipePdf(
          settings.backendUrl,
          settings.tandoorHost,
          settings.tandoorToken,
          recipeId
        );
        const title = document.title.replace(/\s*[|·-]\s*Tandoor.*$/i, "").trim() || `rezept-${recipeId}`;
        triggerBlobDownload(blob, `${title}.pdf`);
        status.textContent = "Fertig!";
      } catch (err) {
        console.error("Tandoor2xcookybooky:", err);
        status.textContent = `Fehler: ${err.message}`;
      } finally {
        button.disabled = false;
        setTimeout(() => (status.textContent = ""), 8000);
      }
    });

    wrapper.appendChild(button);
    wrapper.appendChild(status);
    return wrapper;
  }

  function findKeywordsAnchor() {
    // Tandoor (Vuetify) renders keywords as a v-chip-group with no stable
    // id/class we can rely on across versions, so we heuristically pick the
    // first chip group inside the main content area.
    const main = document.querySelector("main") || document.body;
    const chipGroups = main.querySelectorAll(".v-chip-group");
    for (const group of chipGroups) {
      if (group.offsetParent !== null) {
        return group.closest("[class]") || group;
      }
    }
    return null;
  }

  function insertButton() {
    if (document.getElementById("tandoor2pdf-button")) return true;
    const anchor = findKeywordsAnchor();
    const button = buildButton();
    if (anchor && anchor.parentNode) {
      anchor.parentNode.insertBefore(button, anchor.nextSibling);
      return true;
    }
    return false;
  }

  if (insertButton()) return;

  const observer = new MutationObserver(() => {
    if (insertButton()) observer.disconnect();
  });
  observer.observe(document.body, { childList: true, subtree: true });

  // Fallback: if we can't find a good anchor after a while, show a floating
  // button instead of giving up silently.
  setTimeout(() => {
    if (document.getElementById("tandoor2pdf-button")) return;
    observer.disconnect();
    const wrapper = buildButton();
    wrapper.style.position = "fixed";
    wrapper.style.bottom = "20px";
    wrapper.style.right = "20px";
    wrapper.style.zIndex = "9999";
    wrapper.style.boxShadow = "0 2px 8px rgba(0,0,0,0.3)";
    document.body.appendChild(wrapper);
  }, 6000);
})();

// Injected (dynamically registered, see options.js) on the configured Tandoor
// instance's /recipe/* pages. Adds a small PDF icon button right below the
// recipe keywords, in the info panel next to the recipe image.

(function () {
  const RECIPE_ID_MATCH = window.location.pathname.match(/\/recipe\/(\d+)/);
  if (!RECIPE_ID_MATCH) return;
  const recipeId = RECIPE_ID_MATCH[1];

  if (document.getElementById("tandoor2pdf-button")) return;

  function findReferenceIconButton() {
    // Copy classes from Tandoor's own "..." menu icon button (v-btn--icon)
    // so our button matches the current theme (light/dark) automatically.
    return document.querySelector("button.v-btn--icon");
  }

  function buildIconButton() {
    const wrapper = document.createElement("span");
    wrapper.id = "tandoor2pdf-wrapper";
    wrapper.style.display = "inline-flex";
    wrapper.style.alignItems = "center";
    wrapper.style.gap = "6px";

    const button = document.createElement("button");
    button.id = "tandoor2pdf-button";
    button.type = "button";
    button.title = "Als PDF herunterladen (xcookybooky)";

    const reference = findReferenceIconButton();
    if (reference) {
      button.className = reference.className;
    } else {
      button.style.cssText =
        "width:36px;height:36px;border-radius:50%;border:1px solid #888;background:transparent;cursor:pointer;";
    }

    const icon = document.createElement("i");
    icon.className = "fa-solid fa-file-pdf";
    icon.setAttribute("aria-hidden", "true");
    button.appendChild(icon);

    const status = document.createElement("span");
    status.id = "tandoor2pdf-status";
    status.style.fontSize = "0.8em";
    status.style.opacity = "0.85";

    button.addEventListener("click", async (event) => {
      event.preventDefault();
      event.stopPropagation();
      button.disabled = true;
      icon.className = "fa-solid fa-spinner fa-spin";
      status.textContent = "Erzeuge PDF …";
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
        icon.className = "fa-solid fa-file-pdf";
        button.disabled = false;
        setTimeout(() => (status.textContent = ""), 8000);
      }
    });

    wrapper.appendChild(button);
    wrapper.appendChild(status);
    return wrapper;
  }

  function findKeywordsContainer() {
    // The keywords render as plain <a class="v-chip" href="/advanced-search?keywords=..."> links
    // inside a wrapping <div class="mt-4">. No more specific hook exists, so we
    // anchor on that href pattern, which is stable regardless of theme/version.
    const link = document.querySelector('a.v-chip[href*="/advanced-search?keywords="]');
    if (link) {
      return link.closest("div") || link.parentElement;
    }
    return null;
  }

  function findInfoPanel() {
    // The right-hand info card (title, author, keywords, metrics) next to the image.
    return document.querySelector(".v-card-text.flex-grow-1");
  }

  function insertButton() {
    if (document.getElementById("tandoor2pdf-button")) return true;

    const keywordsContainer = findKeywordsContainer();
    if (keywordsContainer && keywordsContainer.parentNode) {
      const wrapper = buildIconButton();
      wrapper.style.display = "block";
      wrapper.style.marginTop = "4px";
      keywordsContainer.parentNode.insertBefore(wrapper, keywordsContainer.nextSibling);
      return true;
    }

    // Recipe has no keywords (so the keywords div isn't rendered): fall back
    // to appending inside the same info panel, still "next to the image".
    const infoPanel = findInfoPanel();
    if (infoPanel) {
      const wrapper = buildIconButton();
      wrapper.style.display = "block";
      wrapper.style.marginTop = "8px";
      infoPanel.appendChild(wrapper);
      return true;
    }

    return false;
  }

  if (insertButton()) return;

  const observer = new MutationObserver(() => {
    if (insertButton()) observer.disconnect();
  });
  observer.observe(document.body, { childList: true, subtree: true });

  // Last-resort fallback: if the expected layout isn't found at all after a
  // while (very different Tandoor version), show a floating button so the
  // feature still works instead of silently doing nothing.
  setTimeout(() => {
    if (document.getElementById("tandoor2pdf-button")) return;
    observer.disconnect();
    const wrapper = buildIconButton();
    wrapper.style.position = "fixed";
    wrapper.style.bottom = "20px";
    wrapper.style.right = "20px";
    wrapper.style.zIndex = "9999";
    wrapper.style.background = "rgba(0,0,0,0.6)";
    wrapper.style.padding = "6px 10px";
    wrapper.style.borderRadius = "8px";
    document.body.appendChild(wrapper);
  }, 6000);
})();

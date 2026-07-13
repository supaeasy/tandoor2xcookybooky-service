// Shared helpers for reading/writing extension settings and talking to the
// backend PDF service. Loaded both by content scripts (as a classic script,
// see options.js registration) and by extension pages via <script>.

const SETTINGS_KEY = "tandoor2pdf_settings";

function normalizeOrigin(url) {
  try {
    const u = new URL(url);
    return u.origin;
  } catch {
    return null;
  }
}

async function getSettings() {
  const data = await chrome.storage.local.get(SETTINGS_KEY);
  return (
    data[SETTINGS_KEY] || {
      tandoorHost: "",
      tandoorToken: "",
      backendUrl: "",
    }
  );
}

async function saveSettings(settings) {
  await chrome.storage.local.set({ [SETTINGS_KEY]: settings });
}

async function requestRecipePdf(backendUrl, host, token, recipeId) {
  const response = await fetch(`${backendUrl.replace(/\/$/, "")}/api/recipe/${recipeId}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ host, token }),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Server-Fehler (${response.status}): ${detail.slice(0, 500)}`);
  }
  return await response.blob();
}

async function requestAllRecipesPdf(backendUrl, host, token) {
  const response = await fetch(`${backendUrl.replace(/\/$/, "")}/api/recipes/all`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ host, token }),
  });
  if (!response.ok) {
    const detail = await response.text();
    throw new Error(`Server-Fehler (${response.status}): ${detail.slice(0, 500)}`);
  }
  return await response.blob();
}

function triggerBlobDownload(blob, filename) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 10000);
}

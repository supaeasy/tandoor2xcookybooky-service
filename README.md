# Tandoor to PDF (xcookybooky)

Browser extension + Docker backend to turn recipes from [Tandoor](https://github.com/TandoorRecipes/recipes)
into nice-looking PDFs using the [Tandoor2xcookybooky](https://github.com/supaeasy/Tandoor2xcookybooky)
approach (Jinja2 → LaTeX → the `xcookybooky` package) — one at a time via a button on the recipe page,
or collected into a single cookbook PDF via the extension's menu.

Since browsers can't run Python or LaTeX themselves, a small Docker container (meant to run on your NAS,
e.g. via Portainer) fetches recipes through the Tandoor API and compiles the PDF. The backend itself
holds no credentials — the Tandoor host and API token are sent by the browser with every request.

## 1. Start the backend container (NAS / Portainer)

1. Copy the `backend/` folder to your NAS (or point Portainer directly at this git repo).
2. In Portainer: **Stacks → Add stack**, using `backend/docker-compose.yml` (build context must point
   at the `backend/` folder), then deploy.
   - The first build downloads the full TeX Live image (several GB) — this takes a while.
   - Default port in the compose file: `8123` (container-internal `8080`).
3. Once it's up, check `http://<NAS-IP>:8123/healthz` — it should return `{"status":"ok"}`.

Optional environment variables (adjustable in `docker-compose.yml`):
- `LATEX_PDF_AUTHOR` — author metadata shown in the PDF (default: `Tandoor`)
- `LATEX_BABEL_LANG` — language for hyphenation/headers, e.g. `ngerman`, `nswissgerman`, `english`

## 2. Create a Tandoor API token

In Tandoor: `[Tandoor URL]/api/access-token/` → create a token with `read` scope and note it down.

## 3. Load the extension

1. Open `chrome://extensions` (or `about:debugging` in Firefox) and enable developer mode.
2. "Load unpacked" → select the `extension/` folder.
3. Click the extension icon → "Change settings" (or right-click → Options) and fill in:
   - **Tandoor instance URL**: e.g. `https://tandoor.my-domain.com`
   - **API token**: the token you just created
   - **Backend server URL**: e.g. `http://192.168.1.50:8123`
4. Save → the browser will ask for permission to access these two addresses; confirm.
5. Reload a recipe page in Tandoor → a small PDF icon button appears in the top toolbar next to the
   search button whenever you're viewing a recipe.

## Downloading all recipes as a collected PDF

Click the extension icon → "📚 All recipes as PDF". This builds a single cookbook PDF with a table of
contents, one chapter per recipe, and page breaks in between. For large recipe collections this can take
several minutes (fetching images, then a single compile pass); progress is shown live in the popup, and
the job keeps running in the background even if you close the popup — the download starts automatically
once it's done.

## Notes

- The backend is intentionally stateless (no stored token) and meant for use on your own LAN (CORS is
  open, `*`). Don't expose it unprotected to the internet.
- PDF layout/appearance (`xcookybooky.cfg`, `backend/templates/preamble.tex.j2`) can be tuned in the
  backend folder; rebuild the container after changes.

---

# Tandoor zu PDF (xcookybooky) — Deutsch

Browser-Erweiterung + Docker-Backend, um Rezepte aus [Tandoor](https://github.com/TandoorRecipes/recipes)
mit dem [Tandoor2xcookybooky](https://github.com/supaeasy/Tandoor2xcookybooky)-Ansatz (Jinja2 → LaTeX →
`xcookybooky`-Paket) als hübsches PDF herunterzuladen — einzeln per Button auf der Rezeptseite, oder
gesammelt als ein Kochbuch-PDF über das Erweiterungsmenü.

Da Browser weder Python noch LaTeX ausführen können, übernimmt ein kleiner Docker-Container (gedacht
zum Betrieb auf deinem NAS, z.B. via Portainer) das Abrufen der Rezepte über die Tandoor-API und die
Kompilierung zu PDF. Die Erweiterung selbst enthält keine Zugangsdaten-Logik am Server – Host und Token
werden bei jeder Anfrage vom Browser mitgeschickt.

## 1. Backend-Container starten (NAS / Portainer)

1. Repo-Ordner `backend/` auf dein NAS kopieren (oder Portainer direkt auf dieses Git-Repo zeigen lassen).
2. In Portainer: **Stacks → Add stack**, `backend/docker-compose.yml` verwenden (Build-Kontext
   muss auf den `backend/`-Ordner zeigen), deployen.
   - Der erste Build lädt das volle TeX-Live-Image (mehrere GB) – das dauert.
   - Standardport im Compose-File: `8123` (Container intern `8080`).
3. Nach dem Start prüfen: `http://<NAS-IP>:8123/healthz` sollte `{"status":"ok"}` liefern.

Optionale Umgebungsvariablen (in `docker-compose.yml` anpassbar):
- `LATEX_PDF_AUTHOR` – Autor-Metadaten im PDF (Default: `Tandoor`)
- `LATEX_BABEL_LANG` – Sprache für Trennung/Überschriften, z.B. `ngerman`, `nswissgerman`, `english`

## 2. Tandoor-API-Token erstellen

In Tandoor: `[Tandoor-URL]/api/access-token/` → Token mit Scope `read` erstellen und notieren.

## 3. Erweiterung laden

1. `chrome://extensions` (oder `about:debugging` in Firefox) öffnen, Entwicklermodus aktivieren.
2. „Entpackte Erweiterung laden" → Ordner `extension/` auswählen.
3. Auf das Erweiterungssymbol klicken → „Einstellungen ändern" (oder Rechtsklick → Optionen) und ausfüllen:
   - **Tandoor-Instanz-URL**: z.B. `https://tandoor.meine-domain.de`
   - **API-Token**: der eben erstellte Token
   - **Backend-Server-URL**: z.B. `http://192.168.1.50:8123`
4. Speichern → Browser fragt nach Zugriffsrechten für diese beiden Adressen, bestätigen.
5. Eine Rezeptseite in Tandoor neu laden → in der oberen Werkzeugleiste neben dem Suchen-Button
   erscheint ein kleiner PDF-Icon-Button, sobald du ein Rezept ansiehst.

## Alle Rezepte gesammelt herunterladen

Erweiterungssymbol anklicken → „📚 Alle Rezepte als PDF". Erzeugt ein einzelnes PDF-Kochbuch mit
Inhaltsverzeichnis, einem Kapitel pro Rezept und Seitenumbrüchen dazwischen. Bei vielen Rezepten kann
das einige Minuten dauern (Bilder werden geladen, danach einmalig kompiliert); der Fortschritt wird live
im Popup angezeigt, und der Job läuft im Hintergrund weiter, auch wenn du das Popup schließt – der
Download startet automatisch, sobald das PDF fertig ist.

## Hinweise

- Das Backend ist bewusst zustandslos (kein gespeichertes Token) und für den Betrieb im eigenen LAN
  gedacht (CORS ist offen `*`). Nicht ungeschützt aus dem Internet erreichbar machen.
- Layout/Aussehen der PDFs (`xcookybooky.cfg`, `backend/templates/preamble.tex.j2`) lassen sich im
  Backend-Ordner anpassen; nach Änderungen den Container neu bauen.

# Tandoor zu PDF (xcookybooky)

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
2. In Portainer: **Stacks → Add stack**, den Inhalt von `backend/docker-compose.yml` einfügen (Build-Kontext
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
5. Eine Rezeptseite in Tandoor neu laden → unterhalb der Keywords erscheint der Button „📄 Als PDF
   herunterladen (xcookybooky)". Taucht er nicht direkt auf (Vuetify-Layout kann variieren), erscheint
   nach ein paar Sekunden ein schwebender Button unten rechts als Fallback.

## Alle Rezepte gesammelt herunterladen

Erweiterungssymbol anklicken → „📚 Alle Rezepte als PDF". Erzeugt ein einzelnes PDF-Kochbuch mit
Inhaltsverzeichnis, einem Kapitel pro Rezept und Seitenumbrüchen dazwischen. Bei vielen Rezepten kann
das einige Minuten dauern (Bilder werden geladen, danach einmalig kompiliert).

## Hinweise

- Das Backend ist bewusst zustandslos (kein gespeichertes Token) und für den Betrieb im eigenen LAN
  gedacht (CORS ist offen `*`). Nicht ungeschützt aus dem Internet erreichbar machen.
- Layout/Aussehen der PDFs (`xcookybooky.cfg`, `backend/templates/preamble.tex.j2`) lassen sich im
  Backend-Ordner anpassen; nach Änderungen den Container neu bauen.

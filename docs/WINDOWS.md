# Start unter Windows

Der Stadtwerke Analyst läuft lokal mit einer Weboberfläche. Für die Analyse und die PowerPoint-Erzeugung sind weder WSL noch Docker oder Microsoft Office erforderlich.

## Einmal einrichten

1. Das Quellprojekt oder `Stadtwerke-Windows.zip` in einen beschreibbaren Ordner entpacken. Nicht direkt aus dem ZIP starten.
2. [uv installieren](https://docs.astral.sh/uv/getting-started/installation/), beispielsweise in PowerShell mit `winget install --id astral-sh.uv -e`. Danach ein neues Fenster öffnen.
3. `Windows einrichten.cmd` doppelklicken. Das Skript richtet Python 3.12 und die Pakete aus `uv.lock` in einer Windows-Umgebung ein. Für die Downloads wird Internet benötigt.
4. `Stadtwerke starten.cmd` doppelklicken. Die Oberfläche öffnet sich unter http://127.0.0.1:8501/.
5. Im Berichtsarchiv eines der fünf Beispiele öffnen. Für den Zugriff auf die gespeicherten Belege ist kein Modellschlüssel erforderlich; aktuelle Referenzen benötigen Internet.

Bei einer neuen PDF-Analyse in den Modelleinstellungen einen Cloud-Anbieter konfigurieren: [OpenRouter](OPENROUTER.md) oder [KI:connect NRW](KICONNECT.md). Die PDF-Inhalte werden dabei an den gewählten Anbieter übertragen. Schlüssel werden nur lokal gespeichert und zählen nicht zum Quellpaket.

**Ollama ist optional.** Wer ausschließlich lokal analysieren möchte, installiert [Ollama](https://ollama.com/download/windows), wählt den lokalen Anbieter und richtet das passende Modell ein. Nur bei einem ausgewählten lokalen Anbieter lädt das Einrichtungsskript das Modell. Cloud- und Beispielbetrieb erfordern keinen Ollama-Download.

## Rechnerwechsel

Das Paket enthält Quellcode, Starter und die fünf vorbereiteten Beispielanalysen mit relativen Originalpfaden. Die lokale Datenbank entsteht beim Start. Mac-Umgebungen, Modellprogramme, persönliche Sitzungen und Schlüssel werden nicht übertragen. Eine vorhandene Mac- oder Linux-`.venv` wird von der Windows-Einrichtung zurückgewiesen; einen frischen Ordner verwenden.

Eigene PDF-Uploads, Analysen und Ausgaben werden lokal unter `data/` und `outputs/` gespeichert. Diese Ordner bleiben vom Git-Upload ausgeschlossen. Das Projekt während des Betriebs nicht verschieben.

## Fehlerhilfe

- **uv fehlt:** uv installieren und die Einrichtung erneut in einem neuen Fenster starten.
- **Ollama oder Modell fehlt:** nur beim lokalen Anbieter erforderlich; Ollama installieren und das ausgewählte Modell bereitstellen oder einen Cloud-Anbieter wählen.
- **Weitere Startfehler:** `data/runtime/app.log` prüfen; bei lokalem Ollama zusätzlich `data/runtime/ollama.log`.
- **App beenden:** PowerShell im Projektordner öffnen und `Stop-Process -Id (Get-Content .\data\runtime\app.pid)` ausführen. Ein separat gestartetes Ollama läuft unabhängig davon.

## Prüfstand

Analyse, Exporte und Starterregeln sind auf dem Entwicklungsrechner automatisiert geprüft. Ein vollständiger praktischer Windows-Lauf ist noch nicht bestätigt. Die OCR-Bibliothek ist Teil der Projektpakete und benötigt keinen zusätzlichen Cloudschlüssel oder Tesseract-Prozess.

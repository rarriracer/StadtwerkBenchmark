# GitHub-Vorbereitung

Das öffentliche Projekt zeigt Quellcode, Methodik, Tests und fünf vorbereitete Beispielberichte. Lokale Schlüssel, Datenbanken, Sitzungen, Caches, zusätzliche PDFs und erzeugte Ausgaben bleiben auf dem eigenen Rechner.

## Vor dem ersten Upload

```sh
uv run pytest -q
uv run python scripts/check_publish.py
```

Die Prüfung verwendet die tatsächliche Git-Dateiauswahl inklusive `.gitignore`. Wenn noch kein Repository existiert, wird diese Auswahl in einem temporären Git-Verzeichnis ermittelt; das Projekt wird dadurch nicht automatisch veröffentlicht oder mit Git initialisiert. Bekannte persönliche Schlüssel werden nur im Speicher verglichen und nie ausgegeben. Der Check ersetzt keine vollständige Sicherheitsprüfung.

Ein bereinigtes Quellpaket lässt sich zusätzlich erzeugen:

```sh
uv run python scripts/check_publish.py --bundle
```

Das ZIP liegt unter `outputs/Stadtwerke-GitHub.zip`. Entpackt enthält es die vorgesehenen Repository-Dateien. Die größere Solingen-PDF sollte zusammen mit dem übrigen Projekt per Git übertragen werden, statt alle Dateien einzeln über die Weboberfläche hochzuladen.

## Darstellung

Die README erklärt Problem, Ablauf, direkte Erprobung, Grenzen und technische Umsetzung. Das Archiv enthält ausschließlich Flensburg, Karlsruhe, Leipzig, Münster und Solingen. Öffentliche Quellen stehen in `Geschäftsberichte/00_Uebersicht.md`; zusätzliche Testberichte gehören nicht ins Repository. Kleine Quellen-/Layoutausschnitte in den Regressionstests bleiben zur Nachvollziehbarkeit der Extraktionsregeln erhalten.

Eine lokale Beispielanalyse lässt sich ohne Modellschlüssel öffnen. Der Referenzvergleich benötigt Internet; eine neue KI-Analyse benötigt einen lokal konfigurierten Anbieter. Ein öffentlich bereitgestellter App-Server mit persönlichem KI-Schlüssel ist kein Teil dieses Pakets.

Screenshots sollten Berichtserfassung, Themenwahl und einen konkreten Ausblick zeigen. Keine geöffneten Modelleinstellungen mit Schlüsseln fotografieren. PowerPoint-Beispiele können später gezielt als Präsentationsmaterial ergänzt werden.

## Veröffentlichung

Zielrepository: https://github.com/rarriracer/StadtwerkBenchmark. Vor jedem weiteren Push mit `git status` und `scripts/check_publish.py` die konkrete Dateiauswahl prüfen. Ein privates Repository kann zunächst zum Review dienen. Über eine öffentliche Freigabe und eine gewünschte Quellcode-Lizenz entscheidet der Projekteigentümer; den Originalberichten wird dadurch keine neue Lizenz zugeordnet.

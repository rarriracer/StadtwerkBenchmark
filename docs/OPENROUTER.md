# OpenRouter einrichten

## Im OpenRouter-Konto

1. Unter https://openrouter.ai/settings/credits das vorhandene Guthaben prüfen. Für den ersten Test mit wenigen Berichten reichen zunächst 5 USD Guthaben; es wird kein Betrag automatisch aufgeladen.
2. Unter https://openrouter.ai/settings/keys einen normalen API-Schlüssel erstellen, etwa mit Namen `Stadtwerke MVP`.
3. Für diesen Schlüssel ein Gesamtausgabenlimit von 5 USD ohne automatische Rücksetzung setzen. Der serverseitige Schlüsselrahmen begrenzt die Nutzung unabhängig vom Programm.
4. Den angezeigten Schlüssel kopieren. Es wird kein zusätzlicher Qwen-/Alibaba-Schlüssel benötigt.

## In der Anwendung

Oben **Modelleinstellungen** öffnen. **OpenRouter** und **Qwen3-VL 235B Instruct** sind im Formular vorbelegt. Den Schlüssel in das Passwortfeld einfügen und **Einstellungen speichern** anklicken. Anschließend **OpenRouter-Verbindung prüfen** auswählen. Diese Prüfung verwendet den Schlüssel-Endpunkt und startet keine kostenpflichtige Modellauswertung.

Danach einen neuen Bericht hochladen. Für bereits archivierte Fehlversuche den Bericht öffnen und unter **Analyse erneut ausführen** eine vollständige Neuauswertung starten. Das bloße Öffnen eines gespeicherten Berichts ist keine neue Cloudanalyse.

Alternativ ist `OPENROUTER_API_KEY` als Umgebungsvariable möglich; `STADTWERKE_PROVIDER=openrouter` aktiviert den Anbieter. Die Datei `data/runtime/model-settings.json` enthält die lokale Konfiguration und den Schlüssel im Klartext. Auf macOS/Linux wird sie mit Dateirechten 0600 geschrieben. Sie wird nicht in Analyseexporte, LangGraph-Zustand oder das Windows-Paket übernommen. Der Schlüssel muss nicht in dieses Chatfenster eingefügt werden.

## Verarbeitung

- Standardmodell: `qwen/qwen3-vl-235b-a22b-instruct`; alternativ `google/gemini-3-flash-preview`.
- Im Cloudmodus wird jede PDF-Seite ausgewertet, ohne die lokale Vorauswahl nach Themenbegriffen. Eine breite PDF-Seite wird als zwei lesbare Bildhälften übertragen; der komplette Seitentext bleibt enthalten.
- Pro Seite erfolgt ein Modellaufruf mit maximal 8.000 Ausgabetokens und einem JSON-Schema. Unvollständige oder nicht schemakonforme Antworten werden als Fehler ausgewiesen.
- Zahl, Einheit, Jahr und Originalbeleg werden anschließend geprüft. Unklare Angaben werden nicht automatisch freigegeben. Originalzellen können eine visuelle Angabe unabhängig bestätigen.
- Erfolgreiche Seiten erhalten getrennte Cloud-Zwischenspeicher mit Modell-, Jahres- und Seitenbezug. Ein Wechsel von lokalem Modell zu OpenRouter übernimmt beim erneuten Upload keine lokale Gesamtanalyse als Cloudanalyse. Ein ausdrücklich geöffneter Archivbericht bleibt verfügbar.
- Tokenverbrauch und vom Anbieter gemeldete Kosten werden im Bericht gespeichert und angezeigt. Werden Kosten nicht gemeldet, wird kein Nullbetrag erfunden. Bei Wiederaufnahme beziehen sich die gemeldeten Kosten auf die neu angefragten Seiten.
- Ungültiger Schlüssel, fehlendes Guthaben und Anfragelimits stoppen weitere Modellaufrufe. Sonstige Seitenfehler bleiben sichtbar und können erneut ausgewertet werden. Es erfolgt kein stiller Wechsel auf das lokale Modell.
- Der Windows-/macOS-Starter benötigt im konfigurierten OpenRouter-Modus keinen laufenden Ollama-Server. Die Modelleinstellungen bieten OpenRouter, KI:connect NRW und lokales Ollama an. OpenRouter bleibt die Vorgabe; bei gewähltem Ollama-Modell wird der lokale Server beim Speichern vorbereitet. Bestehende lokale Archivanalysen bleiben als solche gekennzeichnet.

## Quellen und Themen

Der eigene Bereich **Quellen & Themen** enthält den allgemeinen Referenzkatalog. **Methodik** beschreibt Prozess, Vergleichsformel und fachliche Grenzen. Die tatsächliche Themenauswahl innerhalb eines Berichts wird weiterhin durch belegte Kennzahlen, passende Einheiten, Perioden und angeschlossene Referenzquellen bestimmt.

## Prüfung

Die Anbindung wurde mit simulierten API-Antworten geprüft: Originalbilder und JSON-Schema im Request, Quellenprüfung, Ablehnung erfundener Zahlen, Kostenprotokoll, Schlüssel-/Budgetfehler, Auswertung aller Seiten, getrennte Cloud-Caches und Start ohne Ollama. Die Oberfläche wurde mit Streamlit AppTest im lokalen und im konfigurierten Cloudmodus geprüft. Ein echter Modellaufruf mit OpenRouter steht noch aus, bis der persönliche Schlüssel lokal hinterlegt ist. Es wurde kein Guthaben für diese Prüfungen verbraucht.

Dokumentation: https://openrouter.ai/docs/api_reference/overview und https://openrouter.ai/docs/guides/features/structured-outputs.

### Statusanzeige

„Schlüssel gespeichert“ bestätigt nur das Vorhandensein eines Schlüssels; es zeigt keinen grünen Verbindungsstatus. „Verbindung geprüft“ erscheint nach erfolgreichem kostenfreiem GET-Schlüsseltest. Ablehnungen werden als „Schlüssel abgelehnt“ angezeigt. Der Prüfstatus gilt maximal eine Stunde und ist an den Hash des aktuellen Schlüssels gebunden; bei einem Schlüsselwechsel ist eine neue Prüfung erforderlich. Der Schlüssel selbst wird nicht im Prüfstatus gespeichert.

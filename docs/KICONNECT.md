# KI:connect NRW einrichten

In den Modelleinstellungen **KI:connect NRW** auswählen. Über https://chat.kiconnect.nrw/app mit dem Hochschulzugang anmelden und im Profil unter API-Schlüsselverwaltung einen Schlüssel erstellen. In der Anwendung den Schlüssel eintragen und ein Modell aus der Auswahl wählen, speichern und **KI:connect NRW-Verbindung prüfen** anklicken. Die Prüfung fragt `/models` ab und kontrolliert, ob der Modellname zugänglich ist; sie startet keine Modellauswertung.

Die feste Basisadresse ist `https://chat.kiconnect.nrw/api/v1`, die Authentifizierung erfolgt mit einem Bearer-Token. Auswertungen verwenden `/chat/completions`. OpenRouter und KI:connect behalten getrennte API-Schlüssel und Modellkonfigurationen. Alternativ können `STADTWERKE_PROVIDER=kiconnect`, `KICONNECT_API_KEY` und `STADTWERKE_MODEL` gesetzt werden. Die Schlüsseldatei bleibt lokal und wird nicht exportiert.

Standardmäßig wird der vollständig extrahierte Seitentext übertragen. **Originalseiten zusätzlich als Bilder senden** nur für ein Modell mit Bildunterstützung aktivieren. Scans und OCR-Stellen bleiben prüfbedürftig. KI:connect erhält JSON-Ausgabeformat plus Antwortschema im Auftrag; jede Antwort wird zusätzlich lokal gegen das Kennzahlenschema und die Quellen geprüft. Nicht alle Hochschulmodelle unterstützen dieselben Ausgabe- oder Bildfunktionen; abgelehnte oder abgeschnittene Antworten werden als Seitenfehler dokumentiert, nicht stillschweigend übernommen.

Die Nutzung zählt gegen das Kontingent der gewählten Nutzendengruppe. API-Schlüssel können ablaufen und müssen gegebenenfalls über KI:connect erneuert werden. Der API-Zugang wurde mit simulierten Antworten geprüft; ein echter Abruf erfordert den persönlichen Schlüssel und einen verfügbaren Modellnamen.

Offizielle Dokumentation: https://help.itc.rwth-aachen.de/service/1808737e10424937b76e564ed15d8028/article/4f07ebbbc8c4477a8db9baa441494941/ und https://chat.kiconnect.nrw/app/api-docs/

## Modelle und Nutzungsgrenzen

Die Modelleinstellungen bieten eine Auswahl mit verständlichen Anzeigenamen; die API-Kennung wird automatisch gespeichert. Die sechs Voreinstellungen sind Mistral Small 4 (119B), Qwen 3.8 (27B), GPT OSS (120B), GPT-6 Luna, GPT-6 Sol und GPT-6 Astra. **KI:connect-Modellliste aktualisieren** lädt die tatsächlich für den gespeicherten Schlüssel verfügbaren Modelle über `/models`; Embedding-Modelle werden ausgeblendet. Die Liste bleibt für diesen Schlüssel lokal gespeichert. Die Verbindungskontrolle aktualisiert sie ebenfalls.

**Nutzung & Limits** zeigt gemeldete Restanfragen, Resttokens und Rücksetzangaben, sofern der Anbieter entsprechende Antwortheader liefert. Bei HTTP 429 werden Nutzungskontingent und Anfragelimit anhand des gemeldeten Fehlercodes unterschieden; ein vorhandener `Retry-After`-Wert wird als Zeitpunkt in deutscher Ortszeit angezeigt. Die letzte Limitmeldung bleibt sichtbar, bis eine Modellanfrage für dieses Modell erfolgreich ist. Die Modelllistenprüfung hebt eine Meldung zum verbrauchten Modellkontingent nicht auf.

Die API-Dokumentation bietet keinen eigenen Endpunkt für das gesamte verbleibende Hochschulkontingent. Fehlen Restwerte, steht deshalb ausdrücklich **von der API nicht gemeldet**. Die zusätzlich gezählten Anfragen und Tokens erfassen nur tatsächliche API-Antworten dieser Anwendung für den ausgewählten Schlüssel und das ausgewählte Modell; sie sind kein Gesamtzähler für die Hochschul-GPT-Nutzung. Über **Kontingent im Hochschul-GPT ansehen** lässt sich das Hochschulkontingent direkt prüfen. Ein Modelllistenabruf kann erfolgreich sein, obwohl das Kontingent für Modellanfragen erschöpft ist.

# Festgelegte Produktentscheidungen

Stand: 7. Oktober 2026. Der vollständige Ablauf steht in [MVP_PLAN.md](MVP_PLAN.md), Quellen in [docs/API_QUELLEN.md](docs/API_QUELLEN.md). Der lokale MVP ist implementiert; aktuelle Qualitäts- und Gestaltungsentscheidungen stehen in [docs/QUALITAET_UND_DESIGN.md](docs/QUALITAET_UND_DESIGN.md).

1. **PDF zuerst analysieren und speichern.** Themen und belegte Kennzahlen werden vor der Nutzerfrage erfasst.
2. **Themen nur bei Datenverfügbarkeit und Vergleichbarkeit anbieten.** Eine öffentliche API allein gibt eine Kennzahlenpaarung nicht frei.
3. **Konstantes Verhältnis als Grundmodell:** `U_ziel = (U_basis / R_basis) × R_ziel`. Kein Ersatz durch ein anderes Treibermodell im ersten MVP.
4. **Drei Szenarien:** unverändertes Verhältnis, −10 %, +10 % als konfigurierbare Annahme; keine statistische Sicherheit behaupten.
5. **Anteil und Preisverhältnis unterscheiden.** SMARD-Haushaltsstrompreise liefern noch keine Haushalts-kWh-Referenz.
6. **Zeitbezug offen ausweisen.** Aktueller Bestand, laufende Jahresmenge und Jahresendschätzung sind verschiedene Ergebnisse; Restjahrannahmen dokumentieren.
7. **LangChain für Sprachaufgaben, LangGraph für Steuerung, Python für Rechnung.** DuckDB hält Fachwerte; persistente Checkpoints halten die Nutzerpause.
8. **Eine PowerPoint-Folie je Thema.** Mehrfachauswahl erzeugt eine gemeinsame Präsentation aus wiederverwendeten Berichtsdaten.
9. **Begrenzte fachliche Rückwege.** Gezielt nachlesen, temporäre Quellenfehler begrenzt wiederholen; ungeklärte Werte bleiben Prüfbedarf.
10. **Zuerst eine passende Sparte vollständig beweisen.** Weitere Themen nach erfolgreichen Quellenverträgen ergänzen. Eine Peer-Unternehmensdatenbank ist keine Voraussetzung.

Der frühere freie Peer-Benchmarking-Vorschlag ist durch diesen Ablauf ersetzt.

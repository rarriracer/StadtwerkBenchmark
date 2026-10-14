# Schwerin 2024: Prüfung vom 8. Oktober 2026

Ausgangsdatei: `Geschäftsberichte/Testberichte/Schwerin_2024.pdf`, 25 PDF-Seiten.
Der erste reguläre Upload erkannte lediglich einen Finanzschuldenwert und ein nicht freigegebenes PV-Projekt. Der Test ist damit fehlgeschlagen.

## Ursache und Korrektur

Grafische Kennzahlenkacheln wurden nicht als zusammengehörige Zellen gelesen. Vier Textspalten auf einer PDF-Doppelseite wurden teilweise in zwei vermischten Regionen ausgegeben. Auch nebeneinander stehende Bilanz-/GuV-Tabellen vermischten Zeilenbeschriftungen und Werte. Die korrigierte Verarbeitung trennt Doppelseiten nur bei einem durchgehend leeren Mittelsteg; Kennzahlenkacheln erhalten Quellenkoordinaten. Das Entfernen doppelter PDF-Zeichen verwendet dieselben Regeln wie pdfplumber, aber eine direkte Indexzuordnung statt wiederholter linearer Suche. Ein negativer Jahresfehlbetrag bleibt eine zulässige Finanzkennzahl.

Die gespeicherte Schweriner Analyse wurde über den normalen Quellen-Refresh neu aus dem PDF gelesen. 25/25 PDF-Seiten wurden verarbeitet; 15 belegte bzw. ausdrücklich als prüfbedürftig gekennzeichnete Einträge wurden gespeichert. Acht Referenzthemen sind auswählbar. Das ist keine Behauptung, dass sämtliche Zahlen des Dokuments oder bereits alle API-Abrufe geprüft wurden.

| Kennzahl | Originalwert | PDF-Seite |
| --- | --- | ---: |
| Stromabsatz | 347 GWh | 2, 6 |
| Gasabsatz | 552 GWh | 2 |
| Wasserabsatz | 5.223 Tm³ = 5.223.000 m³ | 2 |
| Wärmeabsatz im Lagebericht | 316 GWh | 6 |
| Stromkunden | 91.483 | 6 |
| Gaskunden | 21.767 | 6 |
| Mitarbeitende | 360 | 2 |
| Bankverbindlichkeiten | 52.687.549,95 EUR | 12 |
| Umsatz im Einzelabschluss | 228.492.398,74 EUR | 13 |
| Zinsen und ähnliche Aufwendungen | 3.191.240,64 EUR | 13 |
| Jahresfehlbetrag | −95.068,72 EUR | 13 |

Die Übersicht nennt abweichend 315 GWh Wärmeabsatz und 302 Mio. EUR Umsatz. Beide Werte bleiben mit einem Prüfhinweis erhalten. Für Wärme wird der detaillierte Lagebericht verwendet; der Übersichtsumsatz wird nicht als gleich abgegrenzter Einzelabschluss behandelt. Das PV-Projekt mit 10,27 MWp wird weiterhin nicht als installierter Gesamtbestand freigegeben.

Prüfergebnis: 288 Tests bestanden, fünf Tests wegen nicht vorhandener lokaler Originaldateien übersprungen. Neu geprüft wurden Originalkennzahlen, Vorjahresausschluss, unabhängige Textspalten, identisches Ergebnis der Zeichenbereinigung und Quellenzuordnung. Der Quellen-Refresh dauerte im gemessenen Lauf 14,7 Sekunden; ein neuer Modelllauf ist darin nicht enthalten. Ergebnisdatei: `outputs/schwerin-pruefung/originalzahlen.json`.

## Stade: separate Fehlerdiagnose

Auch Stade enthält operative Kennzahlen: PDF-Seite 16 nennt 180 GWh transportierten Strom und 574 GWh transportiertes Erdgas. Das sind Netzmengen, keine Vertriebsabsätze. PDF-Seite 17 nennt 2,31 Mio. m³ Wasserabgabe; Seite 18 nennt 1.158 kWp eigene Anlagen und 256 kWp im Contracting; Seite 19 nennt 123 Ladepunkte. Die vollständige Korrektur und Prüfung für Stade steht noch aus. Ein stärkeres Textmodell allein behebt unvollständige Kandidatenerfassung, vermischte Spalten und fehlende Jahresbelege nicht.

OpenRouter ist noch nicht angebunden; die bisherige Modellanbindung verwendet ChatOllama mit lokalem Textinput.

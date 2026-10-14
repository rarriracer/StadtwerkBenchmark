# Solingen – Upload und Referenzvergleich

Prüfung am 8. Oktober 2026 mit dem gelieferten `SW_Solingen_GB_2024-2025.pdf`.

## Ursache und allgemeine Korrektur

Die alte Jahreskolonnenerkennung akzeptierte einzelne Kalenderjahre, aber keine Geschäftsjahresbezeichnungen wie `2024/2025` oder `2024/25`. Dadurch wurden die Kennzahlentabellen vollständig übersprungen. Eine beiläufige Nennung „Geschäftsjahr 2025“ auf Seite 34 wurde stattdessen als Berichtsjahr ausgewählt; die vorher gespeicherte Analyse enthielt null Beobachtungen.

Die Erkennung unterstützt jetzt ausdrücklich beschriftete Geschäftsjahreskolonnen. Der vollständige Periodentext bleibt als Quellenangabe erhalten. Bei wiederholten Zeilen „Verkaufsmenge“ wird die Sparte aus der unmittelbar vorherigen Strom-/Gas-/Wasser-Umsatzzeile übernommen und als zusätzlicher Tabellenbeleg gespeichert. Die Regeln verwenden keine fest hinterlegten Solinger Kennzahlen.

Unterschiedlich große Schriften in einer gemeinsamen Kopfzeile werden bei Unternehmensüberschriften berücksichtigt. Netzlängen, Hausanschlüsse und Zähler werden fachlich getrennt von Kundenanzahlen erfasst. Ein nachgewiesener Gesamtumsatz erhält Vorrang vor einzeln ausgewiesenen Segmentumsätzen; die Segmentwerte bleiben gespeichert.

## Gegen das Original geprüfte Kernwerte

| PDF-Seite | Kennzahl | Originalzahl | Normalisierter Wert |
|---|---|---|---|
| 59 | Stromverkaufsmenge | 456,951 Mio. kWh | 456.951 MWh |
| 59 | Gasverkaufsmenge | 869,133 Mio. kWh | 869.133 MWh |
| 59 | Wasserverkaufsmenge | 10,518 Mio. m³ | 10.518.000 m³ |
| 60 | Gesamtumsatzerlöse | 312.950 T€ | 312.950.000 EUR |
| 60 | Bilanzsumme | 335.864 T€ | 335.864.000 EUR |
| 60 | Jahresüberschuss | 4.876 T€ | 4.876.000 EUR |
| 60 | Investitionen | 22.008 T€ | 22.008.000 EUR |
| 62 | Wassernetz | 599,0 km; 32.831 Hausanschlüsse; 33.101 Zähler | entsprechend getrennte Kennzahlen |
| 62 | Gasnetz | 492,7 km; 25.941 Hausanschlüsse; 36.533 Zähler | entsprechend getrennte Kennzahlen |
| 62 | Stromnetz | 1.654,4 km; 35.054 Hausanschlüsse; 109.755 Zähler | entsprechend getrennte Kennzahlen |

Zusätzlich vier Segmentumsätze auf Seite 59: Strom 122,4 Mio. EUR, Gas 86,6 Mio. EUR, Wasser 26,4 Mio. EUR und Verkehr 19,2 Mio. EUR. Insgesamt 20 fachlich zugeordnete, belegte Berichtskennzahlen; sieben Themen mit angeschlossenen Referenzen.

## Geschäftsjahr und Referenzen

Die [offizielle Unternehmensseite des Versorgers](https://www.stadtwerke-solingen.de/ueber-uns/unternehmen/) nennt Oktober bis September. Diese Quelle ist als geprüfter Kalender in `data/reporting-calendars.json` gespeichert; die Anwendung ordnet ihn anhand der Herausgeberdomain im Impressum zu. Eine zweijährige Jahresbezeichnung allein erlaubt keine frei erfundenen Monatsgrenzen. Ohne belegte Grenzen verweigert die Rechnung einen Geschäftsjahres-Mengenvergleich.

Für 2024/2025 liegt die vollständige historische Referenzperiode somit zwischen 1. Oktober 2024 und 30. September 2025. Der SMARD-Adapter lädt jetzt auch Zwischenjahre. Der Mengenanteil verwendet die vollständige Geschäftsjahressumme; die Veränderung vergleicht dieselben Kalendermonate innerhalb der historischen Periode. Die Periodenherkunft bleibt in Oberfläche und Analyse-JSON sichtbar.

Alle sieben Themen wurden erfolgreich mit aktuellen öffentlichen Referenzen ausgeführt: Strommenge bis September 2026, Gasmenge bis August 2026, Wasserpreisindex bis August 2026, Marktpreis bis September 2026, Kreditzins bis August 2026. Finanz- und Wasserpreisanalysen liefern Kontext ohne automatische Unternehmenshochrechnung.

## Prüfung des normalen Ablaufs

Der Bericht wurde im regulären LangGraph-Ablauf gegen eine zunächst leere Berichtsdatenbank eingelesen; es wurden keine vorgefertigten Beobachtungen eingesetzt. Alle 64 Seiten wurden gelesen. Zwei Seiten benötigten lokale OCR. Die ergänzende lokale Modellauswertung betraf drei ausgewählte Seiten; bereits vorhandene Modellantworten konnten teilweise wiederverwendet werden. Die Kernwerte stammen aus Originaltabellen und festen Regeln.

Anschließend wurden alle sieben Themen ausgewählt, die realen Referenzen abgerufen und PowerPoint-/CSV-/JSON-Exporte erzeugt. Der erste Referenzlauf deckte die fehlende Zwischenjahresabfrage des Stromadapters auf; nach ihrer Korrektur bestanden alle sieben Vergleiche. Ergebnisprotokoll: `outputs/solingen-pruefung/workflow-result.json`; Exporte sind dort unter `files` verlinkt. Die frühere leere Analyse bleibt als Prüfdatei erhalten.

Die Oberfläche wurde mit 20 Berichtskennzahlen, sieben Auswahlthemen, Original-PDF-Popup auf Seite 59, allen sieben Ergebnissen, drei Downloads und dem Wechsel zu einem neuen Upload geprüft. Die Originalseiten 59, 60 und 62 wurden visuell kontrolliert. Neue Regressionen sichern Geschäftsjahreserkennung, Spartenübernahme, Vorjahresspalten, Mengen-/Währungseinheiten, technische Netzdaten und den korrekten Referenznenner. 290 automatisierte Tests bestanden. Andere Tabellenzeilen bleiben vollständig im Originaltabellenbereich gespeichert; nicht jede grafische oder fachfremde Angabe ist eine automatisch klassifizierte Kennzahl.

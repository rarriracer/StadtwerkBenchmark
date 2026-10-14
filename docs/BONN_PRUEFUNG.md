# Korrigierter Bonn-Ablauf

Prüfbericht: hochgeladene PDF „Stadtwerke Bonn“, Geschäftsjahr 2025, 60 PDF-Seiten, SHA256 `e7f79b29179156fc9ce1c46b3827329bb56fbaa221f9e88672515d12c9820836`.

## Ursachen des bisherigen Abbruchs

Einige PDF-Seiten enthalten außerhalb der sichtbaren Seitengrenzen Text der benachbarten Seite. Auf PDF-Seite 13 wurde dadurch die Erlöstabelle von Seite 12 mit Gas- und Wärmeabsätzen vermischt. Die Einlesung berücksichtigt jetzt ausschließlich Objekte innerhalb der Seite.

Das kleine lokale Modell änderte Originalzahlen (4.200 wurde beispielsweise 4200), erfand Belegsätze und ordnete Geldbeträge als Energiemengen ein. Der Originalbelegabgleich sperrte diese Kandidaten. Dadurch hatte die Themenauswahl keine freigegebene Kennzahl und startete keinen API-Vergleich. Zusätzlich wurde die Modellauswertung auf eine Auswahl von Seiten begrenzt. Die Oberfläche unterschied das Einlesen aller Seiten und die ergänzende Modellauswertung nicht ausreichend.

Jetzt werden alle Seiten nach expliziten Originalzahlen durchsucht. Eindeutige Textstellen werden mit Zahl und Beleg direkt übernommen. Die ergänzende Modellauswertung hat in der Oberfläche kein Seitenlimit mehr. Geldbeträge können nicht als Absatzmengen freigegeben werden. Alte Analysen werden vor der Neuauswertung archiviert.

## Abgrenzung des PV-Vergleichs

PDF-Seite 20, auch visuell geprüft:

> Bis Ende des Jahres 2025 waren auf städtischen und SWB-Liegenschaften Anlagen mit rund 2.400 kWp in Betrieb.

Das entspricht rund 2,4 MWp. Vergleichsgegenstand ist genau der Standortbestand auf diesen Liegenschaften. Eigentum, Beteiligungsverhältnisse und ein gesamter SWB-Bestand werden daraus nicht abgeleitet. Die zusätzliche Angabe von 4.200 kWp einschließlich privater und gewerblicher Projekte bleibt zur Prüfung gespeichert, weil „umgesetzt“ nicht eindeutig den aktuellen Betrieb und dieselbe Abgrenzung beschreibt.

## Referenz und Rechnung

Die [Energy-Charts-API](https://api.energy-charts.info/v2/installed_power?country=de&time_step=monthly), Reihe `solar_dc`, nennt 118.067 MWp zum 31.12.2025 und 130.361 MWp zum 30.09.2026. Rohdaten in GW werden umgerechnet. Oktober wird als laufender Monat ausgeschlossen. Abruf und Prüfsumme sind in der Analyse gespeichert.

`2,4 × 130.361 / 118.067 = 2,649905562 MWp`

Referenzwachstum: 10,4127 %. Ausgangsanteil: 0,002032744 %. Bedingter Vergleichswert: rund 2,65 MWp. Abgeleitete Veränderung zum Bericht: rund 0,25 MWp bzw. 250 kWp. Szenarien mit ±10 %: rund 2,38 / 2,65 / 2,91 MWp.

Diese Rechnung zeigt das Ergebnis bei konstantem Anteil zum September-Stichtag. Sie ist weder ein beobachteter aktueller Bonn-Wert noch eine Jahresendprognose. Eine tatsächliche Über- oder Untererfüllung lässt sich erst mit einem aktuellen Wert desselben Unternehmensportfolios feststellen.

## Prüfungen

16 automatisierte Prüfungen bestehen. Neue Prüfungen decken das konkrete 2.400-/4.200-kWp-Beispiel, die belegte Abgrenzung des Teilbestands, eine erfundene Abgrenzung, falsche Geld-/Energieeinheiten, Gas/Wärme einschließlich Vorjahreswerten, Text außerhalb der PDF-Seite sowie vollständige Seitensuche und Versionierung alter Analysen ab.

Der reale erneute Lauf wertete 60 Seiten mit der Originalzahlensuche und 13 Seiten ergänzend mit dem installierten lokalen Modell aus. Es gab keine technischen Extraktionsfehler. Vier source-basierte Kennzahlen wurden belegt (Stromabsatz, Gasabsatz, Wärmeabsatz, PV-Teilbestand); nur der PV-Teilbestand besitzt hier einen angeschlossenen passenden Referenzadapter. Die übrigen Modellkandidaten bleiben zur Prüfung gespeichert. Der persistente LangGraph wurde mit PV-Auswahl bis zum Export fortgesetzt. Die Oberfläche wurde mit gespeichertem Bericht, Auswahl, API-Vergleich, sichtbarer Formel, Differenz und Download-Schaltflächen geprüft. Die erzeugte PowerPoint wurde gerendert und visuell geprüft. Ergebnis: `outputs/bonn-2025-vergleich/`.


## Nachprüfung der fünf Berichtsbereiche am 7. Oktober 2026

Der Originalbericht wurde erneut direkt gelesen; die vollständigen Originalseiten 12, 13 und 20 wurden visuell geprüft. Fünf operative Bereiche sind mit konkreten Angaben belegt:

| Bereich | Originalangabe 2025 | PDF-Seite | Abgrenzung |
|---|---|---|---|
| Stromabsatz | 896 GWh, +5,7 % gegenüber Vorjahr | 12 | Gesamtabsatz, keine Haushalts-/Industrieaufteilung |
| Gasabsatz | 1.215 GWh, +6,5 % | 13 | Gesamtabsatz |
| Fernwärmeabsatz | 432 GWh, +1,9 % | 13 | Gesamtabsatz; Vorjahr 424 GWh |
| Photovoltaik | rund 2.400 kWp in Betrieb | 20 | Städtische und SWB-Liegenschaften |
| Ladeinfrastruktur | über 1.800 Ladepunkte Ende 2025 | 20 | Private, gewerbliche und öffentliche Ladepunkte im Bonner Stadtgebiet, kein reiner SWB-Bestand |

Die strengere Jahresprüfung hatte den Stromabsatz zwischenzeitlich wieder ausgeschlossen, weil das kurze Einzelzitat keine Jahreszahl enthielt. Die unmittelbar folgende Erläuterung nennt Preisanpassungen Anfang 2025. Die direkte Regel übernimmt nun beide Sätze als einen zusammenhängenden, im Original geprüften Beleg; Zukunftsplanungen dürfen diesen Zeitbezug nicht herstellen. Ladepunkte werden separat als Anzahl erkannt; „über“ bleibt als Untergrenze erhalten. Die 500 Ladepunkte im Sommer werden nicht zu einem Jahresendbestand umgedeutet; auch die 640 öffentlichen Lademöglichkeiten erhalten ohne eindeutigen Stichtag keine automatische Zuordnung zum Jahresende.

Die gespeicherte Bonn-Analyse wurde ohne neue Modellaufrufe aktualisiert. Die Oberfläche zeigt die fünf Bereiche unter „Belegte Berichtskennzahlen“, einschließlich Originalseite und Verfügbarkeit des Referenzvergleichs. Der nationale Referenzvergleich bleibt nur für PV freigeschaltet, da Strom-, Gas-, Wärmeabsatz und Ladeinfrastruktur noch keinen passenden implementierten Referenzvergleich haben. Die reine Gebietszahl aller Ladepunkte wäre insbesondere nicht direkt mit einer bundesweiten Reihe ausschließlich öffentlich zugänglicher Ladepunkte vergleichbar.

76 Tests bestehen. Ein Test liest die echten Originalseiten und prüft die fünf Kennzahlen, die Untergrenze und die Referenzfreigabe. Ein zusätzlicher Oberflächentest mit der tatsächlichen gespeicherten Bonn-Analyse zeigt fünf belegte Berichtsgrößen ohne Ausführungsfehler. Frühere Beispiel-Exporte und deren Szenarien sind historische Dateien; neue Ausblicke verwenden nur den konstanten Anteilsvergleich.

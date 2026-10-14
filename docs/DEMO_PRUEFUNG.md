# Geprüfter Demo-Ablauf

Prüfung am 7. Oktober 2026 auf Roberts Mac mit 8 GB Arbeitsspeicher.

## Echter Bericht und echte Referenzen

Der öffentliche [RheinEnergie-Lagebericht 2024](https://rheinenergieprod-media.e-spirit.cloud/b75b6766-e548-4eb6-af9d-6a6e09542276/media/documents/veroeffentlichungen/Lagebericht_RheinEnergie.pdf) liegt lokal als `data/raw/RheinEnergie_2024.pdf`. Der Originalbeleg auf PDF-Seite 18, gedruckte Seite 32, wurde visuell geprüft. Der zugehörige PV-Bestand beträgt rund **90 MWp bei RheinEnergie Solar**, nicht bei einem einzelnen Solarpark und nicht als Zubau im Jahr. Der Bericht nennt auf derselben Seite auch 32 MWp für ein Einzelprojekt und 7 MWh Speicherenergie; diese Werte wurden nicht als PV-Gesamtbestand übernommen.

Die allgemeine LangChain-Auswertung mit `qwen2.5:3b` lieferte anfangs eine falsche Belegzuordnung. Eine fokussierte Zweitlesung der expliziten installierten PV-Gesamtleistung mit kleinem JSON-Schema las Zahl und Originalbeleg korrekt. Feste Textregeln ordnen an dieser Stelle den installierten Gesamtbestand zu. Die fehlerhaften ersten Kandidaten bleiben im Bericht zur Prüfung sichtbar. Der Demo-Wert wurde nicht manuell als synthetische Testzahl ersetzt.

Die [Energy-Charts-API](https://api.energy-charts.info/v2/installed_power?country=de&time_step=monthly) lieferte für PV-DC in Deutschland:

| Stichtag | Referenzbestand |
|---|---:|
| 31.12.2024 | 100.785 MWp |
| 30.09.2026 | 130.361 MWp |

Der Oktober-Wert wurde ausgeschlossen, weil der Monat am Prüftag noch läuft. Die API deklariert den Zeitbezug als Monatsende. Rohdaten in GW wurden in MWp umgerechnet. Der Abruf ist mit Zeitstempel und Prüfsumme gespeichert.

## Ergebnis

Der Ausgangsanteil beträgt 0,08930 %. Die bedingte Schätzung zum September-Stichtag beträgt **116,41 MWp**, bei ±10 % liegen die Szenarien bei **104,77 MWp** und **128,05 MWp**. Diese Zahlen sind Rechenszenarien, keine beobachteten aktuellen RheinEnergie-Werte und keine Jahresendprognose.

Das Ergebnis liegt in `outputs/demo-RheinEnergie/`. Die PowerPoint wurde gerendert und die Folie visuell geprüft. Text und Diagramm sind editierbar. Die Oberfläche wurde mit gespeicherter Analyse, Themenauswahl, Referenzabruf und sichtbaren Download-Schaltflächen geprüft.

Der PDF-Dateidialog im Codex-internen Browser ließ sich mit der Browserautomatisierung nicht bedienen. Ein automatisierter Nachweis des Upload-Dialogs liegt deshalb nicht vor. Das Lesen des echten PDFs wurde im vollständigen lokalen Ablauf geprüft. Für eigene Uploads empfiehlt sich der normale Browser, den die Startdatei öffnet.

## Automatisierte Prüfungen

Zehn Prüfungen bestanden: Verhältnisrechnung und Szenarien, Null-/ungültige Referenzen, deutsche Zahlenformate, Originalbeleg und Einheit, falsches Jahr, geplante Anlagen, Zubau, Einzelprojekte, Netzgebiets- und Auslandsmischbestände, widersprüchliche Werte, Monatsende und Einheitenumrechnung sowie persistente Auswahlpause und Wiederaufnahme im tatsächlichen LangGraph. Die automatisierte Graph-Prüfung nutzt gekennzeichnete Testwerte; der vorstehende reale Demo-Ablauf verwendet das installierte Modell und die öffentliche API.

## Praktische Grenze

Auf diesem Rechner läuft ein kleines lokales Modell. Sein Belegabgleich und seine fachliche Zuordnung sind nicht durchgehend zuverlässig. Das MVP unterstützt deshalb prüfbare Originalbelege und eine Korrekturmaske. Sechs Referenzzuordnungen für Anlagenbestände sind implementiert; die übrigen recherchierten Referenzfamilien sind noch nicht an die Oberfläche angeschlossen.

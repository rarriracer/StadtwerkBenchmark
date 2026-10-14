> Ablauf seit 14. Oktober 2026: keine manuellen Zusatzangaben. Auswählbar sind ausschließlich automatisch berechenbare Unternehmensvergleiche. Die unten erwähnten Tarif-/Expositionsszenarien sind ohne vollständig belegte Berichtseingaben nicht aktiv. Alle acht Quellen bleiben angebunden.

## Aktuelle Prüfung: Unternehmensvergleiche, 13. Oktober 2026

Alle acht Quellen bleiben erhalten. Maßgeblich für ihre unternehmensbezogene Nutzung ist jetzt [UNTERNEHMENSVERGLEICHE.md](UNTERNEHMENSVERGLEICHE.md): verfügbare Unternehmensmodelle, sinnvolle zusätzliche Modelle und jeweils erforderliche Eingaben sind getrennt beschrieben. Unternehmensmodelle verwenden ausschließlich automatisch erfasste Berichtsangaben. Manuelle Szenarioeingaben sind aus Themenwahl und Export ausgeschlossen.

# Quellenkatalog für den Stadtwerke-Ausblick

Implementierungsstand **13. Oktober 2026**. Die öffentlichen Schnittstellen sind an Themenwahl, Rechnung und PowerPoint-/CSV-/JSON-Export angeschlossen. Historische Jahre 2024/2025 und aktuelle veröffentlichte Daten 2026 werden nach Zeitbezug geprüft. „Aktuell“ ist der verfügbare Datenstand, nicht zwingend der heutige Tag.

| Vergleich | Implementierte Quelle | Methode |
|---|---|---|
| PV, Wind, Speicherleistung/-energie | Energy-Charts | Bestand Dezember Berichtsjahr gegen letzten abgeschlossenen Monatsendbestand |
| Stromabsatz gesamt | SMARD-Netzlast, Filter 410 | Proportionale Relation zur historischen Jahressumme; aktueller bedingter Mengenwert Januar bis verfügbarer Monat |
| PV-Stromertrag | SMARD-PV-Erzeugung, Filter 4068 | Derselbe Mengenvergleich; Referenzabgrenzung und Standortunterschiede sichtbar |
| Gasabsatz gesamt, SLP, RLM | BNetzA/THE Monats-CSV | Tagesmittel GWh/Tag × tatsächliche Kalendertage; historische Jahressumme und aktueller Zeitraum |
| Haushalts-/Industriestrompreise, Gaspreise | SMARD modellierte Preise | Gleiche historische und aktuelle Monate; eigenes Stromtarifszenario mit Menge, Tarif und Weitergabeannahme. Gaspreise bleiben ergänzender Kontext. |
| Strombeschaffung | Energy-Charts Day-ahead DE-LU | Preisexposition ausschließlich für bestätigte offene Unternehmensmengen; zeitgewichteter DE-LU-Marktpreis. |
| Fernwärme | Open-Meteo ERA5 Temperatur | Ortsbezogener Heizgradtag-Proxy, gleiche Monate; eigener Vergleichsabsatz und Wetteranteil erforderlich. |
| Wetter und Strahlung | Open-Meteo Archiv und Forecast | Historische Strahlungsreferenz; Sieben-Tage-Vorhersage getrennt vom Jahresvergleich |
| Ladeinfrastruktur | BNetzA historische Ladepunktstatistik | Öffentliche Ladepunkte: Stadt bei eindeutigem Treffer, sonst Bundesland/Deutschland; Bestandsmodell nur mit ausdrücklich bestätigter öffentlicher Unternehmenszahl im tatsächlichen API-Gebiet. |
| Fahrzeugmarkt | KBA ArcGIS REST | BEV-Pkw auf Bundeslandebene; Deutschland als Summe aller 16 Länder, Vertraulichkeitskennzeichen beachten |
| Finanzierung | Bundesbank SDMX, EZB-Fallback | Historisches Jahresmittel gegen Mittelwert der verfügbaren aktuellen Monate; Wirkung nur auf betroffene bestätigte Finanzierung und eingegebene Dauer. |
| Trinkwasserabsatz, Wasserbetriebsmengen, Wassernetzeinspeisung | Eurostat HVPI, `prc_hicp_minr`, `coicop18=CP0441`, `unit=I25`, `geo=DE` | Wasserpreisindex für Haushalte; eigener Tarif, Menge und Weitergabe erzeugen bedingten Erlös, keine Mengenprognose. |
| Abwasserbehandlung / Abwassermenge | Eurostat HVPI, `coicop18=CP0443` | Preisindex Abwasserentsorgung; eigenes Tarifszenario mit bestätigter Menge und Weitergabe, keine Hochrechnung der Kubikmeter. |
| Stromerzeugung, Umsatz, EBIT/EBITDA/EBT, Jahresergebnis, FFO, operativer Cashflow | Energy-Charts Day-ahead DE-LU | Strommarktpreis als gemeinsamer externer Einfluss; keine pauschale Übertragung auf Unternehmensgewinne oder Erzeugungsmengen |
| Investitionen, Eigenkapital, Bilanzsumme, dynamischer Verschuldungsgrad, Nettoverschuldungsfaktor, Gearing | Bundesbank / EZB Unternehmenskreditzins | Finanzierungsumfeld; Unternehmenskennzahl behält Originaleinheit und wird nicht automatisch hochgerechnet |

Die auswählbaren Unternehmensmodelle ergeben sich aus eindeutig belegten Berichtswerten. Modelle mit fehlenden Unternehmensangaben stehen nicht zur Auswahl. Die Anzahl der Auswahlmöglichkeiten ist keine Anzahl unabhängiger API-Datenquellen.

Die Eurostat-Abfrage verwendet die neue [HVPI-Klassifikation und Indexbasis](https://ec.europa.eu/eurostat/web/hicp/information-data) mit historischen Rückrechnungen. Die alten Reihen mit Basis 2015 enden 2025 und eignen sich nicht für den aktuellen 2026-Vergleich. [Aktueller Datensatz](https://ec.europa.eu/eurostat/databrowser/view/prc_hicp_minr/default/table?lang=en). Live-Prüfung am 7. Oktober 2026: Wasser und Abwasser bis August 2026, vollständig vergleichbare historische Perioden 2024 und 2025; Rohantworten und Prüfwerte in `outputs/reference-expansion/live-checks.json`.

Der Ausblick kennzeichnet eigene Analysen und Diagramme sichtbar. Bei Mengenvergleichen entsteht eine eigene bedingte Unternehmenskurve; bei Jahresabsatz wird die historische Monatsverteilung ausschließlich aus der nationalen Referenz abgeleitet und entsprechend beschriftet. Das Analyse-JSON speichert diese modellierten Kurven mit ihrem Werttyp. Kontextanalysen bleiben bei externen Preisen, Zinsen oder Wettergrößen.

**Bonn:** fünf belegte Themen sind auswählbar: PV-Ausbau, Stromabsatz, Gasabsatz, Fernwärme und Ladeinfrastruktur. Es werden nur vorhandene freigegebene Berichtskennzahlen angeboten. Finanzierungs-/Kundensegmentthemen erscheinen erst mit passenden Belegen im konkreten Bericht.

**MaStR:** Der persönliche Webdienst-Key fehlt; deshalb ist kein MaStR-Connector freigeschaltet. Die offizielle Dokumentation verlangt diesen Key für Datenabfragen. Zusätzlich muss die Verfügbarkeit historischer Regionalbestände geprüft werden, bevor diese angeboten werden. Netzentgelte und aktuelle lokale Kunden-/Absatzwerte haben im geprüften Quellenbestand keine allgemeine deutschlandweite Schnittstelle.

Technische Rohantworten werden sechs Stunden gecacht, mit tatsächlicher Abrufzeit, Quellenadresse und SHA-256 archiviert. Fehlende Referenzen erscheinen als Fehlerhinweise statt Nullwerte. Eine optionale Zusatzquelle blockiert keinen erfolgreichen Hauptvergleich. Wetterwerte und Fahrzeugbestände werden nicht als gleichartige Mengenreferenz ausgegeben.

Die folgenden Detailtabellen dokumentieren die ursprüngliche Recherche. Maßgeblich für freigeschaltete Berechnungen ist die obige Implementierungstabelle; frühere Szenarioideen sind keine zusätzlichen automatischen Unternehmensprognosen.

## Auswahlpunkte mit nachgewiesener Datenbasis

Die folgenden Themen dürfen in den Kandidatenkatalog. Angezeigt werden sie erst nach Prüfung der Kennzahlen im konkreten Geschäftsbericht. Die Quellen liefern externe Einflussgrößen; keine aktuellen Unternehmenszahlen des hochgeladenen Versorgers.

| Auswahlpunkt | Benötigte Berichtsdaten | Externe Referenz / Schnittstelle | Historie und Stand 2026 | Erlaubte Auswertung |
|---|---|---|---|---|
| Photovoltaik: Ausbau eigener Anlagen | PV-Leistung in MW/MWp, Bilanzierungs-/Beteiligungsumfang, Stichtag | Energy-Charts: `solar_dc` oder `solar_ac` | Monatlich; 2024/25 vollständig, 2026 bis Oktober-Label, aktueller Monat vorläufig | Szenario bei gleichbleibendem Anteil am deutschen Leistungsbestand; keine Prognose der Anzahl installierter Kundenanlagen |
| Photovoltaik: Stromertrag | PV-Erzeugung in MWh; möglichst Leistung, Standorte, Inbetriebnahmen | Open-Meteo: Strahlung, Temperatur | Bonn: 366/365 vollständige Tage 2024/25; 2026 bis 30. September ohne Lücken, plus kurze Wettervorhersage | Wetterabhängiges Ertragsszenario bei explizit angenommenem Anlagenbestand und technischer Verfügbarkeit |
| Windenergie: Ausbau eigener Anlagen | Windleistung in MW, onshore/offshore, Beteiligungen | Energy-Charts: `wind_onshore`, `wind_offshore` | Dieselbe monatliche Abdeckung wie PV | Kapazitätsszenario; Windgeschwindigkeit allein ergibt noch keinen Stromertrag |
| Batteriespeicher: Ausbau | Speicherleistung MW und/oder Energieinhalt MWh | Energy-Charts: `battery_storage_power`, `battery_storage_capacity` | Monatlich 2024/25 und 2026 | Ausbau getrennt nach Leistung und Energieinhalt; keine Erlös- oder Arbitrageprognose |
| Stromvertrieb an Haushalte: Preis-/Erlösszenario | Haushaltsabsatz, zugehöriger Umsatz oder Durchschnittspreis; vergleichbare Abgabenbasis | SMARD: modellierte Neu-/Bestandskundenpreise, optional dynamische Preise | Monatlich 2024/25 vollständig; Januar–August 2026 | Preisentwicklung; Umsatz nur mit separater Mengenannahme und vergleichbarem Netto-/Bruttoumfang |
| Stromvertrieb an Industrie: Preis-/Erlösszenario | Industrieabsatz und zugehöriger Umsatz/Preis; Vergünstigungsprofil | SMARD: Industriepreise mit/ohne Vergünstigungen | Monatlich 2024/25 vollständig; Januar–August 2026 | Industriepreis-Szenario; nicht pauschal auf alle Gewerbe-/Geschäftskunden übertragen |
| Gasvertrieb an Haushalte: Preis-/Erlösszenario | Absatz, zugehöriger Umsatz/Preis, Kundengruppe | SMARD: modellierte Gaspreise Neu-/Bestandskunden | Monatlich 2024/25 vollständig; Januar–August 2026 | Preisentwicklung; keine industrielle Gaspreisreihe in diesem geprüften Feed |
| Gasabsatz Haushalte und kleines Gewerbe | SLP-Gasabsatz MWh/GWh, Gebiet, Geschäftsjahr | BNetzA: SLP-Verbrauchs-CSV; ergänzend Open-Meteo | 52 Wochenwerte 2024/25, bis KW 38/2026 | Szenario entsprechend dem nationalen SLP-Verbrauch; alternativ Wettermodell mit getrenntem Grundverbrauch |
| Gasabsatz Industrie / größere Verbraucher | RLM-Gasabsatz MWh/GWh; Kunden-/Branchenmix | BNetzA: RLM-Verbrauchs-CSV | 52 Wochenwerte 2024/25, bis KW 39/2026 | Nationaler Verbrauchstrend als expliziter Treiber; Strukturabweichung zum lokalen Kundenmix sichtbar machen |
| Fernwärme: wetterabhängiger Absatz | Verkaufte Wärmemenge, Gebiet, angenommener wetterabhängiger Anteil | Open-Meteo: Temperatur → dokumentierter Heizgradtag-Proxy | 2024/25 und laufendes 2026, örtliche Koordinaten | Wettersensitivität der Wärmemenge; keine Ableitung von Netzanschlüssen oder Verkaufspreisen |
| Strombeschaffung / ungesicherte Marktpreisexposition | Beschaffungs-/Erzeugungsmengen, Kosten; ungesicherter Anteil als Berichtswert oder Annahme | Energy-Charts: Day-ahead DE-LU | Vollständige Preiswerte für 2024/25; 2026 bis 6. Oktober | Marktpreis-Sensitivität für explizite offene Mengen; keine automatische Neubewertung aller langfristig beschafften Mengen |
| Finanzierung / Zinsbelastung | Finanzschulden, Zinsaufwand; variabler/refinanzierter Anteil | Bundesbank SDMX oder EZB SDMX: neue Unternehmenskredite >1 Mio. EUR, variabel/Zinsbindung bis 3 Monate | Je 12 Monatswerte 2024/25; Januar–August 2026, letzter Wert vorläufig | Zinsänderung nur auf die betroffene Finanzierung; übrige Schulden behalten vertraglichen Zins |
| E-Mobilität: regionales Marktpotenzial | Ladegeschäft / Ladepunkte / Ladestrom im Bericht für Unternehmensbezug; Gebiet | KBA ArcGIS REST: BEV, Plug-in-Hybride und Anteile | Quartalsstichtage 2024/25 und Januar/April/Juli 2026 | Regionaler Marktvergleich; Ladestrom-/Ausbauszenario nur mit zusätzlicher Annahme zur Kopplung an Fahrzeugbestand |

Biomasseleistung ist im geprüften Energy-Charts-Kapazitätsfeed ebenfalls vorhanden. Sie kann nach demselben Prinzip als weiterer Anlagen-Auswahlpunkt ergänzt werden, falls ein Bericht diese Sparte getrennt ausweist.

## Konkrete Schnittstellen und Nachweise

### 1. Energy-Charts / Fraunhofer ISE

[API und Dokumentation](https://api.energy-charts.info/) · [maschinenlesbare Spezifikation](https://api.energy-charts.info/openapi.json)

```text
GET https://api.energy-charts.info/v2/installed_power?country=de&time_step=monthly
GET https://api.energy-charts.info/v2/price?bzn=DE-LU&start=2024-01-01&end=2026-10-06
```

Ohne Schlüssel getestet, HTTP 200. Kapazitäten: je 12 Monatslabels 2024/25, 10 Labels 2026. Einheiten stehen je Serie: PV/Wind/Speicherleistung GW, Speicherenergie GWh. Mit 1.000 multiplizieren für MW beziehungsweise MWh. **Die Zeitstempel bezeichnen laut API das Berichtsjahr/den Berichtsmonat, die Werte dessen Periodenende.** Das Oktober-Label darf am 6. Oktober nicht als abgeschlossenes Oktober-Ergebnis gelten. Für periodengleiche Vergleiche nur abgeschlossene Monate verwenden und vorläufige Werte gesondert zeigen.

Die monatliche Kapazitätsschnittstelle liefert Deutschland, keinen verifizierten NRW- oder Bonn-Bestand. Der Bundesbestand ist kein durchschnittliches Stadtwerk. MWp/DC und Wechselrichterleistung/AC separat vergleichen. Auch eigene Anlagen, Beteiligungen und Anlagen im Netzgebiet unterscheiden.

Preiswerte tragen EUR/MWh. Die Zeitschritte verändern sich innerhalb des geprüften Zeitraums; Jahresmittel daher nach Intervalldauer gewichten, nicht alle Zeilen gleich gewichten. Eine Leistungsreihe würde entsprechend über Zeit integriert, um MWh zu erhalten. Day-ahead-Werte für spätere Stunden sind bereits festgestellte Auktionspreise, keine Preisvorhersage.

Antworten enthalten eine Lizenzangabe; beim Kapazitätsfeed CC BY 4.0 mit Energy-Charts-Nennung, beim geprüften Preisfeed CC BY 4.0 mit BNetzA/SMARD-Nennung. Rate-Limits, Cache und `Retry-After` beachten. Zusätzliche Erzeugungs- und Kurzfristprognose-Endpunkte sind dokumentiert; ihre Jahresabdeckung wurde hier nicht gesondert geprüft und sie schalten noch keine weiteren Themen frei.

### 2. SMARD / Bundesnetzagentur: Endkunden- und Industriepreise

[Haushaltsstrom](https://www.smard.de/page/home/topic-article/46/218364/modellierte-strompreise) · [Industriestrom](https://www.smard.de/page/home/topic-article/211972/215546/industriestrompreise) · [Haushaltsgas](https://www.smard.de/page/home/topic-article/46/218386/modellierte-gaspreise)

```text
GET https://www.smard.de/resource/blob/217306/-/data-csv-data.csv
```

Dieser öffentliche CSV-Feed wird von der offiziellen Grafikbibliothek eingebunden. Er ist ein direkt nutzbarer Datenexport, **keine zugesicherte, versionierte REST-API**. Quelle/Schema beim Abruf prüfen; die Ressourcenadresse kann sich ändern. Dateien cachen und den nächsten Feed über die offizielle Seite beziehungsweise `mod_urls` entdecken.

Semikolongetrennt, ohne Überschriften: Serie, Monatsdatum, danach Werte. Nachgewiesene Reihen:

| Serien-ID | Werte nach Datum, in Reihenfolge | Einheit |
|---|---|---|
| `s-mdl_stpr-1-1` | Abgaben-/Netzanteil; Beschaffung/Vertrieb/Marge; Neukundenpreis | ct/kWh |
| `s-mdl_stpr-1-2` | Abgaben-/Netzanteil; Beschaffung/Vertrieb/Marge; Bestandskundenpreis | ct/kWh |
| `s-ind_stpr-1-1` | Industriepreis ohne Vergünstigungen; mit Vergünstigungen | ct/kWh |
| `g-mdl_gspr-1-1` | Abgaben-/Netzanteil; Beschaffung/Vertrieb/Marge; Gas-Neukundenpreis | ct/kWh |
| `g-mdl_gspr-1-2` | Abgaben-/Netzanteil; Beschaffung/Vertrieb/Marge; Gas-Bestandskundenpreis | ct/kWh |
| `s-mdl_dyn_stpr-1-1` | Bestandskundenpreis; Neukundenpreis; modellierter dynamischer Preis | ct/kWh |

Jeweils 12 Monate 2024, 12 Monate 2025 und 8 Monate 2026 geprüft. Die modellierten Preise sind nationale Referenzen, keine beobachteten Tarife des konkreten Versorgers. Haushaltspreise nicht direkt mit Netto-Umsatz/MWh vergleichen; Steuern, Netzentgelte und durchlaufende Positionen angleichen. „Beschaffung, Vertrieb, Marge“ ist ein zusammengesetzter Preisbestandteil und keine Unternehmensmarge. Industriereihen passen nicht automatisch zu jeder gewerblichen Abnahme.

### 3. Bundesnetzagentur: Gasverbrauch

[Industrie / RLM](https://www.bundesnetzagentur.de/DE/Gasversorgung/aktuelle_gasversorgung/_svg/GasverbrauchRLM_woechentlich/Gasverbrauch_RLM_W_2023_2.html) · [Haushalte/Gewerbe / SLP](https://www.bundesnetzagentur.de/DE/Gasversorgung/aktuelle_gasversorgung/_svg/GasverbrauchSLP_woechentlich/Gasverbrauch_SLP_W_2023.html)

```text
GET https://www.bundesnetzagentur.de/SiteGlobals/Functions/SVG/_functions/csv_export.html?view=renderCSV&id=870314
GET https://www.bundesnetzagentur.de/SiteGlobals/Functions/SVG/_functions/csv_export.html?view=renderCSV&id=870322
```

HTTP 200, CSV ohne Schlüssel. Kalenderwoche als erste Spalte, danach Jahreswerte. 2024/25 je 52 Werte; 2026 RLM bis KW 39, SLP bis KW 38. Nationaler wöchentlicher Mittelwert in GWh/Tag: **keine wöchentliche Energiemenge**. Periodengrenzen und Tage pro Woche abbilden; Jahresrand-/ISO-Wochen nicht blind als 52 × 7 Tage behandeln. Revisionen speichern. SLP enthält kleine Gewerbekunden, RLM große Verbraucher einschließlich Gaskraftwerken; die Trennung entspricht nicht exakt Privatpersonen versus sämtliche Unternehmen.

### 4. Open-Meteo: örtliches Wetter und kurze Vorhersage

[Historical Weather API](https://open-meteo.com/en/docs/historical-weather-api) · [Forecast API](https://open-meteo.com/en/docs)

```text
GET https://archive-api.open-meteo.com/v1/archive?latitude=50.7374&longitude=7.0982&start_date=2024-01-01&end_date=2026-10-01&daily=temperature_2m_mean,shortwave_radiation_sum&models=era5&timezone=Europe%2FBerlin
GET https://api.open-meteo.com/v1/forecast?latitude=50.7374&longitude=7.0982&daily=temperature_2m_mean,shortwave_radiation_sum&forecast_days=7&timezone=Europe%2FBerlin
```

Bonn-Beispiel, HTTP 200 ohne Schlüssel. Archiv: 366/365 gültige Tageswerte 2024/25; 273 gültige Tageswerte 2026 bis 30. September. Angeforderter 1. Oktober enthält `null`, muss also ausgeschlossen werden. Vorhersage: 6.–12. Oktober 2026. Temperatur °C, Strahlung MJ/m². Historische Werte sind Wetter-Reanalysen, keine lokalen Unternehmensmessungen. ERA5 bewusst festlegen, statt unbemerkt Modelle zwischen Jahren zu wechseln. Modellwechsel am Übergang zur Kurzfristvorhersage kennzeichnen.

Heizgradtage als transparenten Proxy berechnen, z. B. `max(20 − T_mean, 0)` für Tage unter 15 °C. Das ist ohne zusätzliche fachliche Prüfung kein zertifiziertes VDI-Verfahren. Grund-/Prozessverbrauch separat halten. Für PV ist horizontale Strahlung nur ein Ertragsproxy; Anlagenstandort, Ausrichtung, Bestand und Verluste bleiben relevant. Gas/Wärme nicht zusätzlich mit nationalem Wettereffekt und örtlicher Temperatur doppelt korrigieren. Für die verbleibenden Monate eines Jahres braucht es ein eigenes Normalwetter-/Wetterszenario; eine Siebentagevorhersage reicht nicht für das Jahresende.

Kostenlose API für nicht kommerzielle Nutzung; vor kommerziellem Produktbetrieb passenden Tarif oder eigenen Betrieb prüfen. Daten-/API-Nutzungsbedingungen unterscheiden und Attribution speichern.

### 5. Bundesbank / EZB: Finanzierung

[Bundesbank SDMX-Dokumentation](https://statistiken.bundesbank.de/statistiken-en/help-991452?article=bundesbank-sdmx-web-service-api-991448)

```text
GET https://api.statistiken.bundesbank.de/rest/data/BBIM1/M.DE.B.A2A.D.R.1.2240.EUR.N?startPeriod=2024-01&format=csv
GET https://data-api.ecb.europa.eu/service/data/MIR/M.DE.B.A2A.D.R.1.2240.EUR.N?startPeriod=2024-01&format=csvdata
```

Beide HTTP 200 ohne Schlüssel; je 12 Monatswerte 2024/25 und 8 Werte 2026. Deutschland, neue Kredite an nichtfinanzielle Unternehmen über 1 Mio. EUR, variabel oder anfängliche Zinsbindung bis drei Monate; Prozent p. a. August 2026 ist vorläufig. Beide Schnittstellen liefern dieselbe zugrunde liegende Statistik, keine zwei unabhängigen Benchmarks. Bundesbank-CSV hat Metadatenzeilen, Semikolon und Dezimalkomma; EZB-CSV ein anderes Schema.

Rechenansatz für eine reine Sensitivität: `betroffene Schulden × (Referenzzins neu − Referenzzins Basis)` in Dezimalzahlen. Repricing-Zeitpunkt und zeitanteilige Wirkung berücksichtigen. Mit Zinsaufwand/Schulden allein kann der variable Anteil nicht ermittelt werden; ihn als Annahme zeigen. Kein direkter EBITDA-Effekt: Zinsen wirken unterhalb des operativen Ergebnisses. Kreditmarge, Laufzeit und Bonität des Versorgers bleiben eigenständige Faktoren.

### 6. KBA: regionale Elektromobilität

[Offizielles Statistikportal](https://das-kba-statistikportal.hub.arcgis.com/) · [Datensatz-Metadaten](https://www.arcgis.com/home/item.html?id=42111224b0934144ae7187cf1a391737)

```text
Basis: https://services-eu1.arcgis.com/U09msXRZoxesNntH/arcgis/rest/services/FZ%20Pkw%20mit%20Elektro%20Antrieb%20Regionen/FeatureServer/0/query
Parameter: f=json, where=..., outFields=..., returnGeometry=false
```

Öffentliche ArcGIS-REST-Abfragen ohne Schlüssel, HTTP 200. Tabelle enthält Quartalsstichtage von Januar 2023 bis Juli 2026. NRW-BEV-Bestände für alle Stichtage 2024/25 und drei 2026-Stichtage mit tatsächlichen Zahlen geprüft. Bundeslandzeilen durch `Zulassungsbezirk = '' AND Gemeinde = ''` isolieren; sonst aggregierte und lokale Zeilen nicht zusammenaddieren.

Bonn: Gemeindeschlüssel `05314000`, Zulassungsbezirk `05314`. Der veröffentlichte Elektro-Pkw-Anteil ist abrufbar. In Bonn tragen absolute BEV-/Pkw-Bestände in den geprüften Zeilen jedoch Kennzeichen `ZS_… = '.'`, obwohl der numerische Wert `0` ist. **Diese Null ist kein gemessener Bestand.** Kennzeichen auswerten, dann auf NRW-Bestand ausweichen oder nur den lokalen Anteil zeigen. Pagination/`exceededTransferLimit` beachten.

BEV und Plug-in-Hybrid getrennt behandeln; „Elektro-Pkw“ umfasst auch weitere Elektroantriebe. Fahrzeugbestand ist weder Neuzulassungszahl noch Anzahl öffentlicher Ladepunkte. Ein Anteil eignet sich zum Marktvergleich, nicht als Nenner für Ladepunkte je Fahrzeug. Ladestrom hängt zusätzlich von Nutzung, Heimladen und Anbieteranteil ab. Quelle: KBA; Datenlizenz Deutschland Namensnennung 2.0 laut Datensatzmetadaten.

Quartalsstichtage sind Bestände am jeweiligen Monatsbeginn. Zum Unternehmensstichtag 31. Dezember 2024 passt näherungsweise der Registerstichtag Januar 2025, nicht Januar 2024; den einen Tag Unterschied ausweisen. Die für einen Jahrgang vorhandenen vier Quartalswerte sind kein Jahresdurchschnitt oder Jahresendwert.

## Noch nicht freigeben

| Thema / Quelle | Ergebnis der Prüfung | Grund für die Sperre |
|---|---|---|
| Regionale PV-Anzahl/-Leistung und Zuordnung zum Versorger über MaStR | [SOAP-Webdienst](https://www.marktstammdatenregister.de/MaStRHilfe/subpages/webdienst.html), [öffentlicher Gesamtexport](https://www.marktstammdatenregister.de/MaStR/Datendownload) vorhanden | Webdienst verlangt Schlüssel; historisch vollständige, regional passende Bestände/Eigentümer für 2024/25 in dieser Recherche nicht nachgewiesen. Inbetriebnahmedatum im heutigen Register ersetzt keinen damaligen vollständigen Bestand. Erweiterung nach Zugang und geeigneter historischer Validierung möglich. |
| Öffentliche Ladepunkte: regionaler Bestandsausblick | [BNetzA-Schnittstellenseite](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/E-Mobilitaet/Schnittstellen/start.html) bestätigt täglich aktualisierten öffentlichen Datensatz; Exportdateien vorhanden | Konkreter öffentlicher Endpunkt und passende historische 2024/25-Snapshots nicht durchgängig getestet. Aktueller Registerbestand und historische aggregierte Statistik haben teilweise verschiedene Verfahrensumfänge. |
| Anzahl vom Stadtwerk installierter PV-Kundenanlagen | Öffentliches Anlagenregister deckt eine andere Größe ab | Keine universelle historische/aktuelle API für Installationsaufträge und Absatz des konkreten Stadtwerks nachgewiesen. |
| Eigene Netzentgelte, lokale Tarife, Kundenanzahl, Umsatz, Gewinn | Teilweise öffentliche Preisblätter / Berichte | Kein einheitlicher geprüfter historischer und aktueller API-Zugang je Versorger. Historische PDF-Preisblätter können später als eigener dokumentierter Importweg ergänzt werden. |
| Wasser, Abwasser, Abfall, Nahverkehr: aktueller Absatz/Unternehmensergebnis | Unterschiedliche öffentliche Statistiken und lokale Datenportale | In dieser Recherche kein übergreifender Schnittstellenweg mit allen drei Jahren verifiziert. Nicht behaupten, dass solche Daten grundsätzlich nicht existieren. |

## Wie aus Bericht und Referenzen ein Szenario wird

1. Bericht grob auf Sparten und belegbare Kennzahlen prüfen. Gesellschaft, Konzern/Beteiligung, Geschäftsjahr, Region und Einheiten festhalten.
2. Nur Themen anzeigen, für die passende Quellen und die nötigen Berichtsdaten vorhanden sind. Fehlende zentrale Kennzahlen führen zum Ausblenden, nicht zu erfundenen Werten.
3. Für die gewählte Sparte gezielt extrahieren; Berichtsjahr mit Referenzzeitraum abgleichen. Bestände brauchen passende Stichtage, Absatz/Umsatz einen ganzen Zeitraum.
4. Vergleich als Verhältnis, normierte Intensität oder Wachstumsdifferenz bilden. Absolute MW eines Versorgers minus nationale GW ergeben keinen sinnvollen Benchmark. Ein einzelnes Berichtsjahr begründet keine empirisch geschätzte Trajektorie. Vorjahresvergleich im Bericht nur verwenden, wenn belegt.
5. Aktuelles 2026 gegen identische historische Monate/Wochen/Stichtage stellen. Ein Januar–August-Mittel ist kein vollständiger Jahreswert. Unternehmensjahreswert nicht als beobachteten Unternehmens-YTD-Wert ausgeben.
6. Szenarioregel und fehlende Treiber offen ausweisen. Unternehmenskapazität bei konstantem nationalem Anteil beispielsweise `C_2024 × R_2026 / R_2024`, mit kompatiblen Stichtagen und MW/DC-Umfang. Die nationale Marktentwicklung ist kein Beweis für eigene Investitionsprojekte.
7. Für eine Jahresendschätzung bereits veröffentlichte Referenzentwicklung und angenommene Restjahresentwicklung getrennt darstellen. Referenzdatenstand, Veröffentlichungs-/Abrufdatum, Revision, Annahmen und PDF-Seiten ins Ergebnis übernehmen.

Für Bonn-PV würde der erste MVP somit eine **deutsche Ausbau-Referenz und örtliche Wetter-Referenz** anbieten. Ein NRW-/Bonn-PV-Benchmark ist erst nach Erweiterung um eine validierte regionale Anlagenquelle verfügbar. PV-Leistung und PV-Erzeugung sind zwei unterschiedliche Fragen und führen zu verschiedenen Abruf- und Rechenwegen.

## Artefakte und Prüfung

- `data/reference_catalog.json`: maschinenlesbare Themen, Quellen, Berichtsvoraussetzungen und Sperren.
- `data/research/api_checks.json`: HTTP-Status, URL, Abrufzeit, SHA-256 und Zeitabdeckung der abschließenden Abfragen.
- `data/research/`: Originalantworten und zusätzliche Discovery-/Grenzfallchecks, einschließlich KBA-Kennzeichen.
- `scripts/probe_reference_sources.py`: GET-only Prüflauf mit Standardbibliothek. Zeitfenster ist absichtlich auf den Recherchetag festgelegt; für laufenden Betrieb dynamisch und mit Cache zu implementieren.

Erfolgreiche Schnittstellentests belegen die Datenverfügbarkeit, nicht die Genauigkeit einer Unternehmensprognose. Vor Freigabe eines berechneten Ausblicks braucht der konkrete Bericht eine weitere fachliche Prüfung; bei mehreren Berichtsjahren zusätzlich einen Rücktest.

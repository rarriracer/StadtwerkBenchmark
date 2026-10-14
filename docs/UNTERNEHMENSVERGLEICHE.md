> Aktueller Ablauf, 14. Oktober 2026: ausschließlich automatische Berichtserfassung und API-Abruf. Keine manuellen Zusatzannahmen. Die folgenden Formeln beschreiben fachliche Voraussetzungen; nur ausdrücklich als automatisch vorhanden gekennzeichnete Modelle stehen zur Auswahl.

# Unternehmensvergleiche: Prüfung aller acht Quellen

Stand: 13. Oktober 2026. Alle acht Quellen bleiben im Katalog. Eine Kategorie wird nicht allein aufgrund ihrer Bezeichnung ausgeschlossen. Entscheidend sind die verfügbare Unternehmensgröße, passende Referenz und eine nachvollziehbare Verbindung zwischen beiden. Die Modelle verknüpfen belegte Unternehmenszahlen mit passenden API-Reihen. Zusatzmodelle werden nicht mit manuellen Eingaben gerechnet. Alle erforderlichen Mengen, Tarife, Zeiträume und Expositionen müssten im Bericht belegt sein. Offene Erweiterungen werden getrennt benannt.

## 1. Energy-Charts · Fraunhofer ISE

**Unternehmensvergleich:** Unternehmensbestand bei konstantem Referenzanteil; Kostensensitivität offener Strommengen.

**Benötigte Angaben:** Bestand, Einheit, Stichtag und Umfang; für Preise: offene Verkaufs-/Beschaffungsmenge und Zeitraum.

**Rechenansatz:** Bestand × Referenzverhältnis; Preiswirkung = offene Menge × Preisänderung.

**Aktuell:** Automatisches Bestandsmodell vorhanden. Preiswirkung nur bei im Bericht belegter offener Exposition; derzeit kein automatisches Preismodell.

[Quellendokumentation](https://api.energy-charts.info/)

## 2. SMARD · Bundesnetzagentur

**Unternehmensvergleich:** Unternehmensmenge für gleiche Monate; segmentbezogener Preis-/Umsatzvergleich.

**Benötigte Angaben:** Absatz/Erzeugung; für Erlöse: Spartenumsatz oder eigener Preis, Kundengruppe, Preisbasis und Weitergabeannahme.

**Rechenansatz:** Mengenmodell aus Bericht und Verbrauchsreferenz; Segmenterlös = Menge × passender Unternehmenspreis.

**Aktuell:** Automatische Mengenvergleiche vorhanden. Kundentarif-/Erlösmodelle benötigen zusätzliche belegte Spartenangaben und sind derzeit nicht auswählbar.

[Quellendokumentation](https://www.smard.de/page/home/topic-article/46/218364/modellierte-strompreise)

## 3. Bundesnetzagentur · Gas

**Unternehmensvergleich:** Unternehmensabsatz nach passendem Kundensegment und gleichen Monaten.

**Benötigte Angaben:** Vertriebsabsatz, SLP/RLM-Abgrenzung, Geschäftsjahr; abweichenden Kundenmix kennzeichnen.

**Rechenansatz:** Unternehmensjahresabsatz × aktuelle nationale Segmentmenge / nationale historische Jahresmenge.

**Aktuell:** Mengenmodell vorhanden

[Quellendokumentation](https://www.bundesnetzagentur.de/DE/Gasversorgung/aktuelle_gasversorgung/_svg/GasverbrauchSLP_monatlich/Gasverbrauch_SLP_M_2023_2.html)

## 4. Open-Meteo

**Unternehmensvergleich:** Witterungssensitivität des Unternehmensabsatzes; standortbezogene Ertragssensitivität.

**Benötigte Angaben:** Wärmemenge und Ort; wetterabhängiger Anteil oder Grundlast; für PV: Ertrag, Anlagenumfang, Standorte und Verfügbarkeit.

**Rechenansatz:** Gleicher Zeitraum: Wärme = Basiswärme × [(1 − Wetteranteil) + Wetteranteil × Heizgradtagverhältnis].

**Aktuell:** Wetterdaten angebunden. Ohne im Bericht belegten Wetteranteil und passenden Zeitraum kein automatischer Wärmeausblick.

[Quellendokumentation](https://open-meteo.com/en/docs/historical-weather-api)

## 5. Bundesnetzagentur · Ladeinfrastruktur

**Unternehmensvergleich:** Unternehmensanteil am öffentlichen Ladepunktbestand im passenden Gebiet.

**Benötigte Angaben:** Eigene öffentlich zugängliche Ladepunkte, Betreiber-/Beteiligungsumfang, Gebiet und Stichtag.

**Rechenansatz:** Öffentliche Unternehmensladepunkte / öffentliche Referenzladepunkte; bedingter Bestand bei konstantem Anteil.

**Aktuell:** Öffentliche Bestandsdaten angebunden. Ohne belegte öffentliche Unternehmenszahl im passenden Gebiet kein automatischer Unternehmensausblick.

[Quellendokumentation](https://www.bundesnetzagentur.de/DE/Fachthemen/ElektrizitaetundGas/E-Mobilitaet/start.html)

## 6. Kraftfahrt-Bundesamt

**Unternehmensvergleich:** Ladestrom des Unternehmens je regionalem BEV; bedingtes Nachfrageszenario.

**Benötigte Angaben:** Eigener Ladestrom, Gebiet, gleicher Zeitraum; öffentliche/private Ladeanteile und Kopplungsannahme.

**Rechenansatz:** Bedingter Ladestrom = Basisladestrom × BEV-Verhältnis, ausschließlich bei ausdrücklich konstanter Nachfrage-/Marktanteilsannahme.

**Aktuell:** Fahrzeugbestände angebunden. Daraus allein folgt keine Unternehmensladestromprognose.

[Quellendokumentation](https://services-eu1.arcgis.com/U09msXRZoxesNntH/arcgis/rest/services/FZ%20Pkw%20mit%20Elektro%20Antrieb%20Regionen/FeatureServer)

## 7. Bundesbank · EZB als Ersatzquelle

**Unternehmensvergleich:** Zinsänderung auf betroffene Unternehmensfinanzierung; eigene Finanzkennzahlen aus dem Bericht.

**Benötigte Angaben:** Variabel verzinste/refinanzierte Kreditsumme, Zinsbindung, Kreditart, Währung und Zeitraum; zugehöriger Zinsaufwand.

**Rechenansatz:** Zinswirkung EUR/Jahr = betroffene Kreditsumme EUR × Zinsänderung in Prozentpunkten / 100 × Zeitanteil.

**Aktuell:** Zinsdaten angebunden. Ohne im Bericht belegte betroffene Finanzierung und Zinsbindung kein automatischer Zinsausblick.

[Quellendokumentation](https://www.bundesbank.de/de/statistiken/geld-und-kapitalmaerkte/zinssaetze-und-renditen/mfi-zinsstatistik-bestaende-neugeschaeft--650658)

## 8. Eurostat

**Unternehmensvergleich:** Preisvergleich eines eigenen Tarifs; preisbereinigter Spartenumsatz oder explizites Tarifszenario.

**Benötigte Angaben:** Wasser-/Abwasserspartenumsatz oder eigener Tarif, Menge, Kundengruppe, Preisbasis und Zeitraum; Tarifänderungsannahme.

**Rechenansatz:** Preisbereinigter Spartenumsatz = Spartenumsatz / passendes Indexverhältnis; Szenario nur mit ausdrücklich angenommener Tarifweitergabe.

**Aktuell:** Preisindizes angebunden. Ohne passenden eigenen Tarif oder Spartenumsatz kein automatischer Erlösvergleich; keine Mengenprognose aus Preisindizes.

[Quellendokumentation](https://ec.europa.eu/eurostat/web/hicp/methodology)

## Finanzierung genauer abgrenzen

Bundesbank/EZB liefern Zinssätze für unterschiedliche Kreditarten, Neugeschäft/Bestände, Betragsklassen und Zinsbindungen. Der aktuell verwendete Feed beschreibt neue Unternehmenskredite über 1 Mio. EUR mit variabler Verzinsung bzw. Zinsbindung bis drei Monate. Er repräsentiert nicht automatisch jeden bestehenden Stadtwerkekredit. Die EZB-Ersatzquelle verwendet dieselbe deutsche Serienkennung, keine unbemerkte Euroraumreihe.

**Illustrative Sensitivität, keine Unternehmensprognose:** 20 Mio. EUR tatsächlich betroffene Kredite × 0,5 Prozentpunkte / 100 = 100.000 EUR zusätzliche Jahreszinsen. Bei nur sechs Monaten Zinswirkung sind es 50.000 EUR. Eine unbesicherte Marktzinsänderung ist nicht automatisch die vertragliche Änderung eines einzelnen Darlehens. Marge, Zinsbindung, Refinanzierungsdatum und Sicherungsinstrumente müssen berücksichtigt oder ausdrücklich als unveränderte Modellannahme dokumentiert werden. Vom Zinsaufwand des Gesamtunternehmens oder vom Eigenkapital wird kein pauschaler Marktzinsmultiplikator abgeleitet.

Eigenkapitalquote (Eigenkapital / Bilanzsumme), Zinsdeckung und Verschuldungskennzahlen können zusätzlich aus gleich abgegrenzten Berichtsdaten berechnet werden. Eine Jahresänderung eigener Finanzkennzahlen ist ein Berichtvergleich, keine durch die Bundesbank gemessene Unternehmensentwicklung. Bei Zinsdeckung oder Cashflow-Verhältnissen dürfen ungeeignete/fehlende Nenner nicht als Null ergänzt werden.

## Einheitliche Freigaberegel

- Ein Unternehmenswert benötigt Originalbeleg, Einheit, Zeitraum und Unternehmens-/Spartenumfang.
- Markt-/Zins-/Wetter-/Preiswerte benötigen eine passende Region, Serie und Zeitbasis.
- Zusätzliche Parameter wie Wetteranteil oder offene Kreditsumme sind belegte Unternehmensangaben aus dem automatisch gelesenen Bericht; keine manuellen oder stillen Standardwerte.
- Annahmen ergeben einen bedingten Vergleich oder eine Sensitivität. Sie sind keine gemessenen aktuellen Unternehmenswerte.
- Fehlende Angaben werden konkret benannt. Das Thema bleibt sichtbar, ohne erfüllte Voraussetzungen wird kein auswählbarer Unternehmensvergleich angeboten.
- Eine technische Datenverfügbarkeit beweist noch kein fertiges Unternehmensmodell.

## Prüfung der bestehenden Datenclients

Die acht vorhandenen Datenclients wurden am 13. Oktober 2026 mit Karlsruhe/Baden-Württemberg als Ortsbeispiel geprüft. Alle lieferten auswertbare Daten, teils aus noch gültigen Antwortcaches. Zeitstände und tatsächlich gespeicherte Abrufzeiten stehen in `data/research/company-source-audit-2026-10-13.json`. Beim Ladepunkt- und Fahrzeugclient erfolgte der Vergleich auf Bundeslandebene; daraus wird keine kommunale Karlsruhe-Reihe behauptet. Laufende bzw. vorläufige Monate werden nicht als abgeschlossene Vergleichsperioden behandelt.

Die Bundesnetzagentur beschreibt inzwischen auch einen tagesaktuellen Webservice für das Ladesäulenregister. Die bestehende Anwendung nutzt weiterhin die historische XLSX-Statistik; ein Wechsel benötigt eine eigene Prüfung der Schnittstelle und ihrer historischen Abdeckung.

## Automatischer Ablauf

Die Auswahl enthält dieselben automatisch ausführbaren Vergleiche wie die Zusammenfassung. Beschäftigte und Ausbildung zählen zusammen als ein Vergleich. Berichtswerte ohne belastbare API-Verknüpfung bleiben in der Kennzahlenübersicht sichtbar. Alle acht Quellen bleiben im Katalog.

Es gibt keine Formulare für zusätzliche Mengen, Tarife, Kredite oder Kopplungsanteile. Frühere Szenarioergebnisse mit manuell eingegebenen Annahmen werden aus Anzeige und Export ausgeschlossen. Originalberichtszahlen und passende automatische Bestands-, Mengen- und Personalvergleiche bleiben erhalten.

# Auswertungsqualität und Gestaltung

Stand: 7. Oktober 2026.

## Warum der erste Bonn-Vergleich nicht startete

1. Das PDF enthielt Textobjekte der Nachbarseite außerhalb der sichtbaren Seitenfläche. Erlöstabelle und Absatztext wurden vermischt.
2. Das kleine lokale Modell änderte Zahlenformate, erfand Belegsätze und ordnete Geldbeträge fälschlich als Energiemengen ein.
3. Der Bericht nannte unterschiedliche PV-Portfolios: rund 2.400 kWp im Betrieb auf städtischen/SWB-Liegenschaften sowie 4.200 kWp umgesetzte Anlagen einschließlich privater/gewerblicher Projekte. Eigentum, Betriebszustand und Abgrenzung waren nicht gleich.
4. Der Belegabgleich gab keinen passenden Wert frei. Der LangGraph startete daher keinen API-Vergleich. Die Oberfläche erklärte diese Pause nicht ausreichend.

Die Auswertung liest jetzt nur sichtbare Objekte, durchsucht alle Seiten nach expliziten Originalzahlen und verbindet Zahlen unmittelbar mit ihren Einheiten. Bei einem anhaltenden Textspaltengutter werden zwei Absatzspalten nacheinander gelesen; numerische Tabellen werden nicht pauschal geteilt. Das lokale Modell ergänzt die Auswertung. Originalbeleg und fachliche Vergleichsfreigabe sind getrennte Statusangaben.

## Allgemeine Regeln für deutsche Versorger

- Keine Sonderfälle nach Stadt- oder Unternehmensnamen. PV-DC/AC, Wind an Land/auf See und Batteriespeicher-Leistung/Energieinhalt werden nach Einheiten und ausdrücklich genanntem Kontext erkannt.
- Bestand, Planung und Zubau bleiben getrennt. Auch der Stichtag wird einer Originalzahl zugeordnet, statt jeden Wert dem Berichtsjahr zuzuschreiben.
- Ein klar bezeichnetes installiertes Teilportfolio kann verglichen werden. Seine Abgrenzung bleibt erhalten; daraus wird kein Gesamtbestand des Stadtwerks und keine Eigentumsaussage.
- Das [OpenPLZ-Ortsverzeichnis](https://www.openplzapi.org/de/sources/) unterstützt lokale kommunale Portfolios. Die kommunale Zuordnung beruht auf einer öffentlichen API, nicht auf einem Bonn-Sonderfall. Ortsantwort, Abrufdatum und Prüfsumme werden lokal gespeichert. Die Geografie eines gesamten Konzernbestands wird nicht aus dem Firmensitz abgeleitet.
- Fehlende oder mehrdeutige Standorte benötigen eine fachliche Bestätigung. Die Korrekturmaske unterstützt Gesamt- und Teilbestände; Text und Zahl werden weiterhin im Original geprüft.
- Text-PDFs und Kalenderjahre ab 2024 sind unterstützt. OCR, eine zuverlässige automatische Interpretation jeder Tabelle und alle Absatz-/Finanzreferenzen sind noch nicht umgesetzt. Es gibt keine Zusage, dass jeder deutsche Geschäftsbericht ohne fachliche Prüfung vollständig extrahiert wird.

35 automatisierte Prüfungen decken die Rechnung, Originalbelege und Einheiten, acht unterschiedliche Ortskontexte (gekennzeichnete Testdaten), die verschiedenen Ausbau-/Speicherdimensionen, Auslandshinweise, Stichtage, Nachbarseitentext, zwei Textspalten, Cacheversionierung sowie LangGraph-Pause, Fortsetzung und tatsächlich gemeldeten Prozessfortschritt ab.

Die echten vorhandenen PDFs von Bonn (60 Seiten), Marburg (44 Seiten), Berliner Wasserbetrieben (101 Seiten) und STAWAG (161 Seiten) wurden für die Einlesung und Originalzahlensuche verwendet. Die ergänzende Modellauswertung für Bonn wurde vollständig ausgeführt. Die Textprüfung der übrigen drei PDFs ist kein Nachweis einer vollständigen erfolgreichen Modellauswertung oder freigegebenen Unternehmensprognose. Gefundene Ziele, Einzelprojekte und unklare Portfolios blieben zur Prüfung gesperrt.

## Neuer Arbeitsbereich

- Weiß, Anthrazit, ruhige Linien und ein zurückhaltender violetter Diagrammakzent. Keine grünen oder blauen Statusflächen.
- Drei Bereiche: Analyse, Berichtsarchiv, Methodik. Ein geöffnetes Dokument führt direkt zur Themenwahl bzw. zum Ergebnis.
- Sechs sichtbare Prozessschritte: Bericht, Extraktion, Belegprüfung, Themenwahl, Referenzen, Ausblick. Die laufende Analyse meldet aktuelle Seite und Bearbeitungsstand. Vier tatsächliche LangGraph-Knoten sind auf der Methodikseite grafisch erklärt.
- Ergebnisse zeigen Berichtswert, bedingten Vergleichswert, abgeleitete Veränderung und nationales Referenzwachstum.
- Die nationale Kurve verwendet echte monatliche Referenzdaten als Index. Der Ausblick enthält einen Vergleichswert für das aktuelle Jahr ohne Szenarioauswahl.
- Die Herleitung verbindet Originalstelle, historische/aktuelle Referenzen, Ausgangsanteil und Formel. Quellen und Prüfsummen sind einsehbar.
- Downloads für editierbare PowerPoint, Vergleichstabelle und Analyse mit Quellen. Die Folien übernehmen die zurückhaltende Diagrammgestaltung.

Gestaltung und Berechnung bleiben getrennt: `assets/app.css` und `src/stadtwerke/ui.py` gestalten den Arbeitsbereich, die Fachlogik liegt in Extraktion, Referenzadapter und Berechnung.


## Reaktion auf lange Analysen

Die Oberfläche wartet nicht mehr synchron auf den Modellaufruf. Ein einzelner lokaler Hintergrundauftrag führt den Workflow aus; eine Streamlit-Fragmentansicht fragt den gespeicherten Fortschritt jede Sekunde ab. Laufzeit, Schritt und Seitenzähler bleiben sichtbar. Mehrfachstarts werden abgewiesen und die Navigation bleibt nutzbar. Der Worker enthält keine Streamlit-Ausgaben. Ein Serverneustart beendet laufende Aufträge; es ist kein dauerhaftes Jobsystem.

Originalbelege und fachliche Vergleichsfreigabe werden getrennt gezählt. Die vorhandene RheinEnergie-Analyse wurde ohne neue Modellaufrufe erneut gegen die sichtbaren PDF-Seiten geprüft: 8 Kandidaten haben einen bestätigten Originalbeleg, aber keine Kennzahl besteht alle Freigaberegeln. Das Archiv nennt die gespeicherten Prüfgründe. Eine Ortszuordnung unterstützt ausschließlich ausdrücklich örtliche kommunale Teilbestände und ersetzt keinen Nachweis für einen vollständigen Anlagenbestand.

45 Tests bestehen. Ein kontrollierter Oberflächentest prüft Navigation während eines blockierten Test-Modellaufrufs, sichtbaren Seitenfortschritt, gesperrte Mehrfachstarts und Ergebnisübernahme.


## Gezielte Prüfung und Rechnerlast

Die allgemeine Ortseingabe wurde aus Upload und Archiv entfernt. Referenzwerte bleiben national; bestehende oder automatisch ermittelte Standortnachweise bleiben Quellenkontext für ausdrücklich örtliche kommunale Teilbestände. Das Prüfangebot betrifft stattdessen den konkreten Bestand und kann belegte Kandidaten vorbefüllen. Die unveränderten Freigaberegeln trennen bestätigte Quellen von fachlicher Vergleichbarkeit.

Nicht bestätigte Belegtexte, falsche Jahre und falsche Dimensionen bleiben für die technische Nachvollziehbarkeit gespeichert und werden in der normalen Kennzahlenansicht nicht angezeigt. Die gespeicherte STAWAG-Analyse hat 36 solche Kandidaten, darunter 30 nicht bestätigte Belegtexte. Dies belegt eine schwache Modellauswertung, nicht 36 sinnvolle Prüfaufgaben. Fehlende gültige Werte werden dadurch nicht erfunden oder nachträglich freigegeben.

Lokales Qwen2.5:3b: Modell wird im finally-Abschnitt nach der Modellauswertung entladen, auch wenn alle Modellseiten fehlschlagen. Keep-alive zwischen Aufrufen 60 Sekunden statt zehn Minuten, CPU-Threads zwei; Kontext bleibt bei 8192, um keine zusätzliche Kürzung der Berichtsausschnitte einzuführen. GPU-Last während der Analyse wird dadurch nicht begrenzt. 48 Tests bestehen, einschließlich Prüfgruppen und Freigabe des Modells bei Fehlern.


## Direkte Originalseitenprüfung

Der Prüfdialog zeigt Originalseite, präzisen Bildausschnitt (nur bei genau einem Zahl-/Einheitenpaar), Seitentext und vorbefülltes Formular. Korrekturen sind optional; Bestätigung umfasst weiterhin den installierten Bestand in Deutschland zum Berichtsjahresende und die Abgrenzung. Ein Originalausschnitt ist keine neue fachliche Freigabe. Eine einzelne unveränderte PDF-Seite kann heruntergeladen werden. Der Viewer verwendet plattformübergreifendes PDFium; keine zusätzliche Systeminstallation von Poppler ist erforderlich.

Spaltenlesung berücksichtigt außermittige Zwischenräume, Schriftgrundlinien mit kleinen Höhenunterschieden und unterschiedliche Spaltenlängen. Numerische Tabellen und Vollbreitenabsätze behalten ihre Reihenfolge. Ein Belegabgleich darf ausschließlich Leerraum und eindeutige Zeilentrennung normalisieren. Die zurückgegebene Originalspanne wird gespeichert; abweichende Zahlen, Einheiten und Wörter werden weiter abgewiesen. Keine unscharfe Ähnlichkeitssuche gibt Kennzahlen frei. 58 Tests bestehen, einschließlich Originalspanne, asymmetrischer Spalten, PDF-Seitenimport, Seitengrenzen und eindeutiger Bildausschnittzuordnung.


## Vereinfachte Auswahl und strenger Jahresbezug

Zieljahr ist automatisch das aktuelle Jahr. Szenario-Regler und Szenariodarstellung entfallen; neue Folien und Tabellen vergleichen Berichtswert und bedingten Vergleichswert. Berichtstitel bzw. wiederkehrende beschriftete Berichtsköpfe bestimmen das Berichtsjahr. Unbeschriftete Prognose- oder Publikationsjahre sind keine Grundlage; ein mehrdeutiger Berichtstitel wird nicht geraten.

Der Validator prüft die Jahreszuordnung unabhängig vom Modell am Originalbeleg. Explizite Jahresenddaten werden der exakten Zahl zugeordnet; fehlende oder widersprüchliche Jahresbezüge werden ausgeschlossen. Direkte Regeln behalten abweichende Originaljahre in den Rohdaten. Auch als installierter Bestand fehlklassifizierte Planungen werden nicht freigegeben. Nicht bestätigte oder fehlende Zahlen erscheinen nicht als Prüfaufgaben. Eine vollständige korrekte Erfassung beliebiger Tabellen ist damit weiterhin nicht garantiert.

Zitate stehen in Anführungszeichen und öffnen als native, auch per Tastatur bedienbare Schaltflächen die zugehörige Originalseite im Dialog. Die vorhandene Originalseitenprüfung und manuelle Ergänzung bleiben erhalten; der allgemeine Alle-Seiten-Browser entfällt. 64 automatisierte Prüfungen bestehen, darunter echte Streamlit-Dialogausführung, automatische Titeljahre sowie falsch oder gar nicht belegte Jahreszuordnungen. Eine neue visuelle Browserprüfung war durch die Browser-Sicherheitsrichtlinie blockiert; der Dialog wurde über Streamlits Oberflächentest ausgeführt.


## Direkte Bestätigung und neutrale Ansprache

Die gezielte Prüfung bietet einen direkten Button „Kennzahl bestätigen“. Originaltext und Korrekturen sind ausklappbar; weder ein vorgelagerter Dialog noch eine zusätzliche Checkbox sind für die Bestätigung nötig. Der Klick bestätigt die sichtbare fachliche Abgrenzung. Automatisch geprüfte Originalzahlen, Einheiten und Jahresbezüge können durch die Bestätigung nicht umgangen werden; ausdrücklich geplante Bestände bleiben gesperrt. Die Bestätigung erhält einen Zeitstempel, und die frühere Beobachtung bleibt als überholt gespeichert. Unterschiedliche Teilbestände werden nicht pauschal überschrieben; ein bestätigter Gesamtbestand wird für den Vergleich gegenüber Teilbeständen bevorzugt.

„Themenabdeckung und Auswahlgrundlage“ unterscheidet auswählbare Größen, offene fachliche Bestätigungen, fehlende passende Bestände und noch nicht angebundene Referenzvergleiche. Im gespeicherten Bonn-Bericht ist PV-DC auswählbar (rund 2.400 kWp auf städtischen/SWB-Liegenschaften). Windbeteiligungen liefern keine belegte installierte Leistung in MW, Batteriespeicher werden als Prüfvorhaben erwähnt. Gas- und Wärmeabsatz sind belegte Berichtsangaben, ihre Referenzvergleiche sind noch nicht umgesetzt.

Die Oberfläche verwendet neutrale Formulierungen wie „Relevante Themen auswählen“ und „Analyse exportieren“. 73 Tests prüfen unter anderem die direkte Ein-Klick-Bestätigung, unverändert wirksame Quellenprüfungen, getrennte Teilbestände und die Begründung der Themenauswahl.

# Prüfung des Berichtsarchivs

Stand: 2026-10-08. 5 archivierte Berichte. Die Prüfung liest das Archiv; sie verändert keine Analyse und startet keine Modell- oder Referenzanfragen.

Geprüft werden PDF-Prüfsumme, Zahl und Reihenfolge der Originalseiten, archivierte Kontrollwerte gegen unabhängig festgelegte Erwartungen, offene Prüfhinweise, technische Fehler und Regelversionen. Diese Kontrolle beweist nicht, dass jede Zahl sämtlicher Berichtsseiten semantisch vollständig erkannt wurde.

| Bericht | Jahr | Seiten vollständig | Kontrollwerte | Offene Zahlen | Vergleichsthemen | Aktuelle Regeln | Einordnung |
|---|---:|---|---:|---:|---:|---|---|
| Stadtwerke Flensburg | 2024 | 26/26 ✓ | 4/4 | 0 | 4 | ja | Kandidat für Schlussprüfung |
| Stadtwerke Karlsruhe | 2024 | 59/59 ✓ | 9/9 | 0 | 4 | nein | Kandidat; Regeln aktualisieren |
| Stadtwerke Leipzig | 2024 | 68/68 ✓ | 11/11 | 0 | 9 | nein | Kandidat; Regeln aktualisieren |
| Stadtwerke Münster | 2023 | 55/55 ✓ | 20/20 | 0 | 8 | nein | Kandidat; Regeln aktualisieren |
| Stadtwerke Solingen | 2025 | 64/64 ✓ | 16/16 | 0 | 7 | nein | Kandidat; Regeln aktualisieren |

## Empfohlene Auswahl

Flensburg, Karlsruhe, Leipzig und Münster sind Kandidaten ohne offene Zahlenprüfungen und mit unabhängigen Kontrollwerten. Solingen ist ein zusätzlicher Kandidat für ein abweichendes Geschäftsjahr. Vor dem Festsetzen sind ihre gespeicherten Analysen auf die aktuellen Layout- und Quellenregeln zu aktualisieren und die Kontrollen erneut auszuführen.



## Was „fertig“ hier bedeutet

Kein Bericht erhält derzeit die Freigabe „vollständig perfekt analysiert“. Der nächste überprüfbare Stand ist ein Beispielarchiv mit festgelegtem Kennzahlenumfang, belegten Werten, aktuellen Regeln, geklärten Prüfhinweisen und einem erfolgreichen Referenz- und Exportlauf. Die automatischen Kennzahlenfreigaben allein ersetzen den unabhängigen Kontrollkatalog nicht.

Diese Prüfung ruft keine Live-Referenzen ab. Vorhandene frühere Referenzläufe (beispielsweise Solingen) sind separat dokumentiert; sie belegen nicht den aktuellen Ablauf nach den letzten Änderungen. Eine vollständige OpenRouter-Auswertung wurde für diese Auswahl ebenfalls nicht durchgeführt.

Für Git empfiehlt sich später ein gezielter, reproduzierbarer Beispieldatensatz mit Prüfmanifest statt der gesamten Laufzeitdatenbank. `data/runtime/` ist bereits ausgeschlossen: API-Schlüssel, Sitzungen und Caches werden dadurch nicht als Beispielarchiv übernommen. Die fünf ausgewählten gespeicherten Analysen werden als portable Beispiele mitgeliefert; es wurde nichts veröffentlicht.

Reproduktion: `PYTHONPATH=src .venv/bin/python scripts/audit_archive.py`. Details: `outputs/archive-audit/summary.json`.

## Beispielauswahl in der Anwendung

Das Standardarchiv zeigt die fünf ausgewählten Berichte. Andere Analysen wurden aus dem Archiv entfernt; neue Uploads werden weiterhin aufgenommen.

| Bericht | Themen | Kategorien |
|---|---:|---|
| Stadtwerke Flensburg | 4 | Gas, Strom, Wasser, Wärme |
| Stadtwerke Karlsruhe | 4 | Finanzen, Gas, Strom, Wärme |
| Stadtwerke Leipzig | 9 | Finanzen, Gas, Strom, Wärme |
| Stadtwerke Münster | 8 | Finanzen, Gas, Strom, Wasser, Wärme |
| Stadtwerke Solingen | 7 | Finanzen, Gas, Strom, Wasser |

„Bericht öffnen · Themen auswählen“ lädt die gespeicherte Analyse direkt in einen Themenwahl-Checkpoint. Dabei werden keine PDF-Seiten neu gelesen, keine Modellanfragen ausgeführt und keine Quellenregeln aktualisiert. Erst die Themenwahl startet den Referenzabruf. Eine Neuauswertung bleibt eine getrennte Aktion.

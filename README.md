# Projekt-Dokumentation Analyse Tool

Dieses Tool durchsucht Projektverzeichnisse, sammelt Dokumentationen und erstellt automatische Zusammenfassungen mit Hilfe von KI.

## Funktionen

- Automatisches Erkennen von Projektordnern
- Extraktion von Dokumentationsdateien (.md, .txt, .docx, .pdf)
- Bewertung der Dokumentationsqualität
- Erstellung von ZIP-Archiven mit Dokumentation
- Kategorisierung in Git-Repositories und lokale Projekte
- **NEU**: KI-basierte Zusammenfassungen der Dokumentation

## Voraussetzungen

```bash
pip install -r requirements.txt
```

## Konfiguration

Die Hauptkonfiguration erfolgt in `extract_documentation_deep.py`:

- `STARTPFADEN`: Pfade, die durchsucht werden sollen
- `MAX_DEPTH`: Maximale Suchtiefe
- `ZIELORDNER`: Ausgabeordner für die Dokumentation
- `ENABLE_SUMMARIZATION`: Aktiviert/deaktiviert die KI-Zusammenfassung
- `USE_OPENAI`: Wählt zwischen lokalem LLM oder OpenAI API

Für die OpenAI API:
1. Kopiere `.env.example` zu `.env`
2. Füge deinen OpenAI API-Key ein
3. Setze `USE_OPENAI = True` in `extract_documentation_deep.py`

## Verwendung

```bash
python extract_documentation_deep.py
```

## KI-Zusammenfassung

Das Tool unterstützt zwei Methoden zur Erstellung von Zusammenfassungen:

### 1. Lokales LLM (Standard)

Verwendet einen lokal laufenden LLM-Server (z.B. LM Studio, Ollama) auf:
- URL: `http://localhost:1234`
- Modell: `mistral` (kann in `summarize.py` angepasst werden)

### 2. OpenAI API

Verwendet die OpenAI API mit GPT-4 (erfordert API-Key in `.env`):
- Setze `USE_OPENAI = True` in `extract_documentation_deep.py`

## Ausgabe

- `alle_dokumentationen/`: Hauptverzeichnis mit allen ZIP-Archiven
- `alle_dokumentationen/best_docs/`: Projekte mit hochwertiger Dokumentation
- `alle_dokumentationen/summaries/`: KI-generierte Zusammenfassungen
- `AI_Zusammenfassung.md`: Wird auch direkt in Projektordnern mit hoher Qualität gespeichert

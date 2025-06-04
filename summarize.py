import os
from docx import Document
import PyPDF2
import requests

def extract_text_from_file(filepath):
    """Extract text content from different file types (.md, .docx, .pdf)"""
    if filepath.endswith(".md") or filepath.endswith(".txt"):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return f.read()
        except UnicodeDecodeError:
            # Try with a different encoding if utf-8 fails
            try:
                with open(filepath, "r", encoding="latin-1") as f:
                    return f.read()
            except Exception as e:
                print(f"Error reading {filepath}: {e}")
                return ""
    elif filepath.endswith(".docx"):
        try:
            doc = Document(filepath)
            return "\n".join([p.text for p in doc.paragraphs])
        except Exception as e:
            print(f"Error reading DOCX {filepath}: {e}")
            return ""
    elif filepath.endswith(".pdf"):
        try:
            reader = PyPDF2.PdfReader(filepath)
            return "\n".join([page.extract_text() or "" for page in reader.pages])
        except Exception as e:
            print(f"Error reading PDF {filepath}: {e}")
            return ""
    return ""

def summarize_project_local(doc_paths):
    """Generate a summary using a local LLM API (e.g., LM Studio, Ollama)"""
    # Filter for text-based files we can extract content from
    text_files = [p for p in doc_paths if os.path.isfile(p) and 
                 (p.endswith(".md") or p.endswith(".txt") or 
                  p.endswith(".docx") or p.endswith(".pdf"))]
    
    if not text_files:
        return "Keine Textdateien zur Zusammenfassung gefunden."
    
    # Extract text from all files
    texts = []
    for file_path in text_files:
        text = extract_text_from_file(file_path)
        if text:
            texts.append(f"--- Datei: {os.path.basename(file_path)} ---\n{text}")
    
    if not texts:
        return "Keine Textinhalte zur Zusammenfassung extrahiert."
    
    full_text = "\n\n".join(texts)
    
    # Limit text length to avoid overwhelming the model
    max_length = 15000  # Characters
    if len(full_text) > max_length:
        full_text = full_text[:max_length] + "...\n[Text gekürzt wegen Längenbeschränkung]"
    
    prompt = f"""
Fasse die Projektdokumentation zusammen (zwischen 500 und 1500 Wörter), strukturiert in:
- Einleitung
- Zielsetzung
- Vorgehensweise
- Ergebnisse
- Erkenntnisse

Text:
{full_text}
"""
    
    try:
        response = requests.post(
            "http://localhost:1234/v1/chat/completions",
            headers={"Content-Type": "application/json"},
            json={
                "model": "mistral",  # oder anderer lokaler Modellname
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3
            },
            timeout=60  # 60 seconds timeout
        )
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return f"Fehler bei der Zusammenfassung: HTTP Status {response.status_code}\n{response.text}"
    
    except Exception as e:
        return f"Fehler bei der Zusammenfassung: {str(e)}"

def summarize_with_openai(doc_paths, api_key=None):
    """Generate a summary using OpenAI API (requires API key)"""
    if not api_key:
        # Try to get API key from environment variable
        api_key = os.environ.get("OPENAI_API_KEY")
        
    if not api_key:
        return "Kein OpenAI API-Key gefunden. Bitte in .env Datei oder Umgebungsvariable setzen."
    
    # Filter for text-based files we can extract content from
    text_files = [p for p in doc_paths if os.path.isfile(p) and 
                 (p.endswith(".md") or p.endswith(".txt") or 
                  p.endswith(".docx") or p.endswith(".pdf"))]
    
    if not text_files:
        return "Keine Textdateien zur Zusammenfassung gefunden."
    
    # Extract text from all files
    texts = []
    for file_path in text_files:
        text = extract_text_from_file(file_path)
        if text:
            texts.append(f"--- Datei: {os.path.basename(file_path)} ---\n{text}")
    
    if not texts:
        return "Keine Textinhalte zur Zusammenfassung extrahiert."
    
    full_text = "\n\n".join(texts)
    
    # Limit text length to avoid overwhelming the model
    max_length = 15000  # Characters
    if len(full_text) > max_length:
        full_text = full_text[:max_length] + "...\n[Text gekürzt wegen Längenbeschränkung]"
    
    prompt = f"""
Fasse die Projektdokumentation zusammen (zwischen 500 und 1500 Wörter), strukturiert in:
- Einleitung
- Zielsetzung
- Vorgehensweise
- Ergebnisse
- Erkenntnisse

Text:
{full_text}
"""
    
    try:
        response = requests.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            },
            json={
                "model": "gpt-4",  # oder gpt-3.5-turbo für günstigere Option
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3
            },
            timeout=60  # 60 seconds timeout
        )
        
        if response.status_code == 200:
            return response.json()["choices"][0]["message"]["content"]
        else:
            return f"Fehler bei der Zusammenfassung mit OpenAI: HTTP Status {response.status_code}\n{response.text}"
    
    except Exception as e:
        return f"Fehler bei der Zusammenfassung mit OpenAI: {str(e)}"

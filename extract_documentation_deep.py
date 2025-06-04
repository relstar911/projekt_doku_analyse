import os
import shutil
import zipfile
import hashlib
import datetime
from pathlib import Path
import dotenv

# Import the summarization module
from summarize import summarize_project_local, summarize_with_openai

# Konfiguration - Diese Werte können durch die UI überschrieben werden
STARTPFADEN = [
    r"C:\Users\ardah",
    r"C:\Users\ardah\CascadeProjects"
]

# Maximum depth to search for projects (relative to STARTPFADEN)
# 1 = only immediate subdirectories of start paths
# 2 = subdirectories and their subdirectories, etc.
MAX_DEPTH = 2  # Adjust as needed
ZIELORDNER = r"C:\Users\ardah\alle_dokumentationen"

# Subfolder for best documented projects
BEST_DOCS_FOLDER = "best_docs"
GIT_CLONES_FOLDER = "git_clones"  # Subfolder for Git repositories
LOCAL_PROJECTS_FOLDER = "local_projects"  # Subfolder for local projects
SUMMARIES_FOLDER = "summaries"  # Subfolder for AI-generated summaries

# Summarization settings
ENABLE_SUMMARIZATION = True  # Set to False to disable summarization
USE_OPENAI = False  # Set to True to use OpenAI API instead of local LLM
MIN_SUMMARIES_PER_RUN = 5  # Minimum number of summaries to create per run
MAX_SUMMARIES_PER_RUN = 10  # Maximum number of summaries to create per run
SUMMARY_BATCH_FILE = "summary_batches.txt"  # File to track which projects have been summarized

# Projekt-Identifikatoren
PROJECT_MARKERS = [
    'README.md', 'README.txt', 'readme.md', 'readme.txt',
    'manifest.json', 'manifest.yaml', 'manifest.yml', 'manifest.xml',
    'docs', 'Docs',
    'package.json', 'pyproject.toml', 'setup.py', 'requirements.txt',
    '.git', 'Pipfile', 'Cargo.toml', 'build.gradle', 'pom.xml', 'composer.json', 'Makefile'
]

DOCS_FOLDERS = ["docs", "Docs", "documentation", "Documentation", "doc", "Doc"]
README_FILES = ["README.md", "README.txt", "readme.md", "readme.txt"]
MANIFEST_FILES = ["manifest.json", "manifest.yaml", "manifest.yml", "manifest.xml"]
OTHER_DOC_FILES = ["LICENSE", "CHANGELOG", "CONTRIBUTING", "CONTRIBUTING.md", "CHANGELOG.md", "LICENSE.md"]

# Minimum quality score to be considered a well-documented project
MIN_QUALITY_SCORE = 3

# Minimum size in bytes for a README to be considered substantial
MIN_README_SIZE = 500

# Hilfsfunktion: Erzeuge einen eindeutigen Ordnernamen

def unique_project_name(path):
    base = os.path.basename(path.rstrip(os.sep))
    hash_part = hashlib.sha1(path.encode('utf-8')).hexdigest()[:8]
    return f"{base}_{hash_part}"

# Prüfen, ob ein Projekt ein Git-Repository ist
def is_git_repository(path):
    """Check if a path is a Git repository."""
    git_dir = os.path.join(path, '.git')
    # Check if .git directory exists
    if os.path.isdir(git_dir):
        return True
    # Check for common Git files
    git_files = ['.gitignore', '.gitmodules', '.gitattributes']
    for git_file in git_files:
        if os.path.isfile(os.path.join(path, git_file)):
            return True
    return False

# Prüfen, ob eine Datei bereits existiert und identisch ist
def is_identical_file(source_path, target_path):
    """Check if two files are identical based on size and hash."""
    if not os.path.exists(target_path):
        return False
    
    # Quick check: file size
    if os.path.getsize(source_path) != os.path.getsize(target_path):
        return False
    
    # Detailed check: file hash (only if sizes match)
    source_hash = hashlib.md5()
    target_hash = hashlib.md5()
    
    with open(source_path, 'rb') as f:
        source_hash.update(f.read())
    
    with open(target_path, 'rb') as f:
        target_hash.update(f.read())
    
    return source_hash.hexdigest() == target_hash.hexdigest()

# Projekt-Root erkennen: Enthält mindestens eine Marker-Datei/-Ordner
def is_project_root(dirpath):
    entries = set(os.listdir(dirpath))
    for marker in PROJECT_MARKERS:
        if marker in entries:
            return True
    return False

# Sammle alle Projekt-Roots (rekursiv, tief)
# Ordner, die übersprungen werden sollen (kurze, effektive Liste)
SKIP_DIRS = {
    '.git', 'node_modules', '__pycache__', '.venv', 'venv', 'env', 'AppData', '.env', 
    'dist', 'build', '.vscode', '.idea', '.mypy_cache', '.pytest_cache', '.cache'
}

COMMON_NON_PROJECT_FOLDERS = {
    "android", "ios", "web", "app", "public", "assets", "Assets.xcassets",
    "tests", "docs", "frontend", "backend", "vendor", "node_modules", "packages", "src"
}

# Helper: Check if path is under any known project root
def is_under_existing_project(root, project_roots):
    for p in project_roots:
        if os.path.commonpath([root, p]) == p and root != p:
            return True
    return False

def find_all_projects(startpaths):
    projects = set() # Use a set to automatically handle duplicates
    
    # Normalize startpaths to absolute paths for reliable comparison
    normalized_startpaths = [os.path.abspath(sp) for sp in startpaths]
    abs_zielordner = os.path.abspath(ZIELORDNER)

    # Core set of directories to always skip
    ALWAYS_SKIP = {
        'node_modules', 'venv', '.venv', 'env', '__pycache__', '.git', '.idea', '.vscode',
        'dist', 'build', 'bin', 'obj', 'target', 'out', 'output', 'Debug', 'Release'
    }

    for spath in normalized_startpaths:
        print(f"Durchsuche: {spath}")
        
        # Track depth relative to start path
        for root, dirs, files in os.walk(spath, topdown=True):
            # Calculate current depth (how many directory levels from start path)
            rel_path = os.path.relpath(root, spath)
            current_depth = 0 if rel_path == '.' else rel_path.count(os.sep) + 1
            
            # Skip if we've exceeded max depth
            if current_depth > MAX_DEPTH:
                dirs[:] = [] # Don't go deeper
                continue
                
            # Skip output directory
            if os.path.abspath(root).startswith(abs_zielordner):
                dirs[:] = [] 
                continue
                
            # Prune problematic directories early
            dirs[:] = [d for d in dirs if not d.startswith('.') and d.lower() not in ALWAYS_SKIP]
            
            # Skip this directory if it's a start path (not a project itself)
            if os.path.abspath(root) in normalized_startpaths:
                continue
                
            # Skip if under an existing project
            if is_under_existing_project(root, list(projects)):
                dirs[:] = [] # Don't look for nested projects
                continue
                
            try:
                if is_project_root(root):
                    abs_path = os.path.abspath(root)
                    projects.add(abs_path)
                    print(f"Projekt gefunden: {abs_path}")
                    dirs[:] = [] # Don't look for projects inside this one
            except PermissionError:
                dirs[:] = [] # Skip inaccessible directories
                continue
            except Exception as e:
                print(f"Fehler bei {root}: {e}")
                continue
                
    return sorted(list(projects))

# Sammle alle relevanten Doku-Dateien/-Ordner im Projekt (rekursiv)
def collect_doc_files(proj_path):
    doc_paths = []
    # When collecting docs within a project, also skip irrelevant subdirectories
    for dirpath, dirnames, filenames in os.walk(proj_path, topdown=True):
        # Prune SKIP_DIRS and hidden directories from dirnames
        dirnames[:] = [d for d in dirnames if not d.startswith('.') and d not in SKIP_DIRS and d.lower() not in {"node_modules", "vendor", "__pycache__", "venv", ".venv", "env"}]
        # Optionally, filter filenames too if needed, e.g., skip all .pyc files
        # filenames[:] = [f for f in filenames if not f.endswith('.pyc')]

        # Docs-Folder
        for d in dirnames:
            if d in DOCS_FOLDERS:
                doc_paths.append(os.path.join(dirpath, d))
        # Einzeldateien
        for fname in filenames:
            # Include standard doc files
            if fname in README_FILES + MANIFEST_FILES + OTHER_DOC_FILES:
                doc_paths.append(os.path.join(dirpath, fname))
            # Include all .md files as they're likely documentation
            elif fname.lower().endswith('.md'):
                doc_paths.append(os.path.join(dirpath, fname))
    return doc_paths

# Evaluate the documentation quality of a project
def evaluate_doc_quality(doc_files, proj_path):
    """Evaluate the quality of a project's documentation.
    Returns a score based on various factors:
    - Presence of README
    - Size of README
    - Number of markdown files
    - Presence of docs folder
    - Total documentation size
    """
    score = 0
    total_size = 0
    readme_size = 0
    md_count = 0
    has_docs_folder = False
    
    for doc_path in doc_files:
        # Check if it's a README file
        basename = os.path.basename(doc_path)
        if basename.lower() in [r.lower() for r in README_FILES]:
            if os.path.isfile(doc_path):
                readme_size = os.path.getsize(doc_path)
                if readme_size >= MIN_README_SIZE:
                    score += 2  # Substantial README
                else:
                    score += 1  # Small README
        
        # Count markdown files
        if doc_path.lower().endswith('.md') and os.path.isfile(doc_path):
            md_count += 1
            total_size += os.path.getsize(doc_path)
        
        # Check for docs folder
        if os.path.isdir(doc_path) and os.path.basename(doc_path) in DOCS_FOLDERS:
            has_docs_folder = True
            # Count files in docs folder
            for root, _, files in os.walk(doc_path):
                for file in files:
                    if file.lower().endswith('.md'):
                        md_count += 1
                    file_path = os.path.join(root, file)
                    if os.path.isfile(file_path):
                        total_size += os.path.getsize(file_path)
    
    # Add points for various quality indicators
    if has_docs_folder:
        score += 2
    if md_count > 5:
        score += 2
    elif md_count > 2:
        score += 1
    if total_size > 50000:  # 50KB
        score += 2
    elif total_size > 10000:  # 10KB
        score += 1
    
    return score

# Kopiere die relevanten Dateien/Ordner in Zielstruktur
def copy_docs(doc_paths, proj_path, dest_dir):
    for src in doc_paths:
        rel = os.path.relpath(src, proj_path)
        dst = os.path.join(dest_dir, rel)
        os.makedirs(os.path.dirname(dst), exist_ok=True)
        if os.path.isdir(src):
            shutil.copytree(src, dst, dirs_exist_ok=True)
        else:
            shutil.copy2(src, dst)

# Hauptfunktion
def load_summarized_projects():
    """Load the list of projects that have already been summarized"""
    batch_file = os.path.join(ZIELORDNER, SUMMARY_BATCH_FILE)
    if not os.path.exists(batch_file):
        return set()
    
    try:
        with open(batch_file, 'r', encoding='utf-8') as f:
            return set(line.strip() for line in f if line.strip())
    except Exception as e:
        print(f"Error loading summarized projects: {e}")
        return set()

def save_summarized_project(project_path):
    """Add a project to the list of summarized projects"""
    batch_file = os.path.join(ZIELORDNER, SUMMARY_BATCH_FILE)
    try:
        with open(batch_file, 'a', encoding='utf-8') as f:
            f.write(f"{project_path}\n")
    except Exception as e:
        print(f"Error saving summarized project: {e}")

def main():
    # Load environment variables from .env file if it exists
    dotenv.load_dotenv()
    
    # Create main output directory and best docs subdirectory
    os.makedirs(ZIELORDNER, exist_ok=True)
    best_docs_dir = os.path.join(ZIELORDNER, BEST_DOCS_FOLDER)
    os.makedirs(best_docs_dir, exist_ok=True)
    
    # Create subdirectories for Git repositories and local projects
    git_clones_dir = os.path.join(best_docs_dir, GIT_CLONES_FOLDER)
    local_projects_dir = os.path.join(best_docs_dir, LOCAL_PROJECTS_FOLDER)
    os.makedirs(git_clones_dir, exist_ok=True)
    os.makedirs(local_projects_dir, exist_ok=True)
    
    # Create directory for AI-generated summaries
    summaries_dir = os.path.join(ZIELORDNER, SUMMARIES_FOLDER)
    os.makedirs(summaries_dir, exist_ok=True)
    
    # Load the list of projects that have already been summarized
    summarized_projects = load_summarized_projects()
    
    projects = find_all_projects(STARTPFADEN)
    print(f"Gefundene Projekte: {len(projects)}")
    
    # Track statistics
    total_projects = 0
    best_projects = 0
    git_projects = 0
    local_dev_projects = 0
    skipped_existing = 0
    
    for proj in projects:
        doc_files = collect_doc_files(proj)
        if not doc_files:
            continue  # Nichts zu extrahieren
        
        total_projects += 1
        proj_folder = unique_project_name(proj)
        zip_path = os.path.join(ZIELORDNER, f"{proj_folder}_dokumentation.zip")
        
        # Check if ZIP already exists and skip if it does
        if os.path.exists(zip_path):
            print(f"{proj_folder}: ZIP existiert bereits unter {zip_path}")
            
            # Still evaluate for best_docs classification if it's a high-quality project
            doc_files = collect_doc_files(proj)
            quality_score = evaluate_doc_quality(doc_files, proj)
            
            if quality_score >= MIN_QUALITY_SCORE:
                best_projects += 1
                
                # Determine if it's a Git repository or local project
                is_git = is_git_repository(proj)
                target_dir = git_clones_dir if is_git else local_projects_dir
                target_zip = os.path.join(target_dir, f"{proj_folder}_dokumentation.zip")
                
                # Only copy if target doesn't exist
                if not os.path.exists(target_zip):
                    try:
                        shutil.copy2(zip_path, target_zip)
                        if is_git:
                            git_projects += 1
                            print(f"{proj_folder}: Git-Repository mit hoher Dokumentationsqualität (Score: {quality_score}) - Kopiert nach {GIT_CLONES_FOLDER}")
                        else:
                            local_dev_projects += 1
                            print(f"{proj_folder}: Lokales Projekt mit hoher Dokumentationsqualität (Score: {quality_score}) - Kopiert nach {LOCAL_PROJECTS_FOLDER}")
                    except Exception as e:
                        print(f"Error copying to categorized folder: {e}")
                else:
                    skipped_existing += 1
                    print(f"{proj_folder}: Bereits in {GIT_CLONES_FOLDER if is_git else LOCAL_PROJECTS_FOLDER} vorhanden")
            
            continue  # Skip to next project since ZIP already exists
        
        # Evaluate documentation quality
        quality_score = evaluate_doc_quality(doc_files, proj)
        
        # Create ZIP file directly without intermediate folder extraction
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            # Track already added files to prevent duplicates
            added_files = set()
            
            for doc_path in doc_files:
                # Calculate the relative path within the project
                rel_path = os.path.relpath(doc_path, proj)
                
                # If it's a directory, add all its contents
                if os.path.isdir(doc_path):
                    for root, _, files in os.walk(doc_path):
                        for file in files:
                            file_path = os.path.join(root, file)
                            # Preserve the directory structure within the ZIP
                            arcname = os.path.join(os.path.relpath(root, proj), file)
                            
                            # Skip if this path was already added to the ZIP
                            if arcname in added_files:
                                continue
                            
                            try:
                                # Create ZipInfo object from file
                                zinfo = zipfile.ZipInfo.from_file(file_path, arcname)
                                
                                # Check and adjust timestamp if before 1980
                                if zinfo.date_time[0] < 1980:
                                    zinfo.date_time = (1980, 1, 1, 0, 0, 0)
                                
                                # Read file content
                                with open(file_path, 'rb') as f_in:
                                    file_data = f_in.read()
                                
                                # Add to zip with compression
                                zipf.writestr(zinfo, file_data, compress_type=zipfile.ZIP_DEFLATED)
                                # Mark as added
                                added_files.add(arcname)
                            except Exception as e:
                                print(f"Error adding {file_path} to ZIP: {e}")
                                continue
                # If it's a file, add it directly
                else:
                    # Skip if this path was already added to the ZIP
                    if rel_path in added_files:
                        continue
                        
                    try:
                        # Create ZipInfo object from file
                        zinfo = zipfile.ZipInfo.from_file(doc_path, rel_path)
                        
                        # Check and adjust timestamp if before 1980
                        if zinfo.date_time[0] < 1980:
                            zinfo.date_time = (1980, 1, 1, 0, 0, 0)
                        
                        # Read file content
                        with open(doc_path, 'rb') as f_in:
                            file_data = f_in.read()
                        
                        # Add to zip with compression
                        zipf.writestr(zinfo, file_data, compress_type=zipfile.ZIP_DEFLATED)
                        # Mark as added
                        added_files.add(rel_path)
                    except Exception as e:
                        print(f"Error adding {doc_path} to ZIP: {e}")
                        continue
        
        # If this is a high-quality documented project, copy the ZIP to appropriate best_docs subfolder
        if quality_score >= MIN_QUALITY_SCORE:
            best_projects += 1
            
            # Determine if it's a Git repository or local project
            is_git = is_git_repository(proj)
            target_dir = git_clones_dir if is_git else local_projects_dir
            target_zip = os.path.join(target_dir, f"{proj_folder}_dokumentation.zip")
            
            try:
                # Only copy if target doesn't exist or is different
                if not os.path.exists(target_zip) or not is_identical_file(zip_path, target_zip):
                    shutil.copy2(zip_path, target_zip)
                    if is_git:
                        git_projects += 1
                        print(f"{proj_folder}: Git-Repository mit hoher Dokumentationsqualität (Score: {quality_score}) - Kopiert nach {GIT_CLONES_FOLDER}")
                    else:
                        local_dev_projects += 1
                        print(f"{proj_folder}: Lokales Projekt mit hoher Dokumentationsqualität (Score: {quality_score}) - Kopiert nach {LOCAL_PROJECTS_FOLDER}")
                else:
                    skipped_existing += 1
                    print(f"{proj_folder}: Bereits in {GIT_CLONES_FOLDER if is_git else LOCAL_PROJECTS_FOLDER} vorhanden")
            except Exception as e:
                print(f"Error copying to categorized folder: {e}")
        else:
            print(f"{proj_folder}: ZIP erstellt unter {zip_path} (Score: {quality_score})")
        
    # Collect projects that need summarization
    projects_to_summarize = []
    for proj in projects:
        if ENABLE_SUMMARIZATION and proj not in summarized_projects:
            doc_files = collect_doc_files(proj)
            if doc_files:
                proj_folder = unique_project_name(proj)
                summary_filename = f"{proj_folder}_zusammenfassung.md"
                summary_path = os.path.join(summaries_dir, summary_filename)
                
                # Skip if summary already exists
                if not os.path.exists(summary_path):
                    projects_to_summarize.append((proj, doc_files, proj_folder))
    
    # Shuffle the list to get a random selection each time
    import random
    random.shuffle(projects_to_summarize)
    
    # Limit to MAX_SUMMARIES_PER_RUN
    projects_to_summarize = projects_to_summarize[:MAX_SUMMARIES_PER_RUN]
    
    # Process summaries
    summaries_created = 0
    for proj, doc_files, proj_folder in projects_to_summarize:
        if summaries_created >= MAX_SUMMARIES_PER_RUN:
            break
            
        print(f"{proj_folder}: Erstelle KI-Zusammenfassung...")
        summary_filename = f"{proj_folder}_zusammenfassung.md"
        summary_path = os.path.join(summaries_dir, summary_filename)
        
        try:
            # Generate summary using either OpenAI or local LLM
            try:
                if USE_OPENAI:
                    summary_text = summarize_with_openai(doc_files)
                else:
                    summary_text = summarize_project_local(doc_files)
                
                # Prüfe auf Fehler in der Zusammenfassung
                if summary_text.strip().startswith("Fehler bei der Zusammenfassung"):
                    print(f"{proj_folder}: Fehler bei der Zusammenfassung – Datei wird nicht gespeichert. {summary_text}")
                    # Versuche es mit der anderen Methode, falls die erste fehlschlägt
                    if not USE_OPENAI and "localhost" in summary_text and ("connection" in summary_text.lower() or "verbindung" in summary_text.lower()):
                        print(f"{proj_folder}: Versuche es mit OpenAI API als Fallback...")
                        fallback_summary = summarize_with_openai(doc_files)
                        if not fallback_summary.strip().startswith("Fehler"):
                            summary_text = fallback_summary
                        else:
                            print(f"{proj_folder}: Auch OpenAI API fehlgeschlagen: {fallback_summary}")
                            continue  # Nicht als zusammengefasst markieren, keine Datei schreiben
                    else:
                        continue  # Nicht als zusammengefasst markieren, keine Datei schreiben
            except Exception as e:
                print(f"{proj_folder}: Ausnahmefehler bei der Zusammenfassung: {str(e)}")
                continue  # Nicht als zusammengefasst markieren, keine Datei schreiben

            # Save summary to file
            with open(summary_path, "w", encoding="utf-8") as f:
                f.write(f"# KI-Zusammenfassung: {os.path.basename(proj)}\n\n")
                f.write(f"Erstellt am: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                f.write(summary_text)
            
            print(f"{proj_folder}: Zusammenfassung gespeichert unter {summary_path}")
            summaries_created += 1
            
            # Mark this project as summarized
            save_summarized_project(proj)
            summarized_projects.add(proj)
            
            # Also save a copy in the project directory if it's a high-quality project
            quality_score = evaluate_doc_quality(doc_files, proj)
            if quality_score >= MIN_QUALITY_SCORE:
                proj_summary_path = os.path.join(proj, "AI_Zusammenfassung.md")
                try:
                    with open(proj_summary_path, "w", encoding="utf-8") as f:
                        f.write(f"# KI-Zusammenfassung: {os.path.basename(proj)}\n\n")
                        f.write(f"Erstellt am: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
                        f.write(summary_text)
                    print(f"{proj_folder}: Zusammenfassung auch im Projektordner gespeichert unter {proj_summary_path}")
                except Exception as e:
                    print(f"Fehler beim Speichern der Zusammenfassung im Projektordner {proj}: {e}")
        except Exception as e:
            print(f"Fehler bei der Zusammenfassung für {proj_folder}: {e}")
    
    # If we didn't create enough summaries, print a message
    if summaries_created < MIN_SUMMARIES_PER_RUN and len(projects_to_summarize) < MIN_SUMMARIES_PER_RUN:
        print(f"Hinweis: Es wurden nur {summaries_created} Zusammenfassungen erstellt, weniger als das Minimum von {MIN_SUMMARIES_PER_RUN}.")
        print(f"Möglicherweise wurden bereits die meisten Projekte zusammengefasst.")
        
        # Check how many projects have been summarized
        total_summaries = len([f for f in os.listdir(summaries_dir) if f.endswith('_zusammenfassung.md')]) if os.path.exists(summaries_dir) else 0
        print(f"Insgesamt wurden bisher {total_summaries} Projekte zusammengefasst.")
        
        # If we've summarized all projects, reset the batch file to start over
        if total_summaries >= len(projects):
            print("Alle Projekte wurden bereits zusammengefasst. Setze Batch-Datei zurück für den nächsten Lauf.")
            batch_file = os.path.join(ZIELORDNER, SUMMARY_BATCH_FILE)
            if os.path.exists(batch_file):
                os.remove(batch_file)
    
    # Create index files for each category
    main_index_path = os.path.join(best_docs_dir, "_index.txt")
    git_index_path = os.path.join(git_clones_dir, "_index.txt")
    local_index_path = os.path.join(local_projects_dir, "_index.txt")
    
    # Count the number of AI summaries created
    summary_count = len([f for f in os.listdir(summaries_dir) if f.endswith('_zusammenfassung.md')]) if os.path.exists(summaries_dir) else 0
    
    # Count the number of summaries created in this run
    new_summaries = summaries_created if 'summaries_created' in locals() else 0
    
    print(f"\n===== Zusammenfassung =====")
    print(f"Gesamt Projekte mit Dokumentation: {total_projects}")
    print(f"Projekte mit hochwertiger Dokumentation: {best_projects} ({int(best_projects/total_projects*100) if total_projects > 0 else 0}%)")
    print(f"  - Git-Repositories: {git_projects}")
    print(f"  - Lokale Projekte: {local_dev_projects}")
    print(f"  - Übersprungene (bereits existierende): {skipped_existing}")
    if ENABLE_SUMMARIZATION:
        print(f"KI-Zusammenfassungen insgesamt: {summary_count}")
        print(f"KI-Zusammenfassungen in diesem Lauf: {new_summaries}")
        print(f"Batch-Einstellungen: Min={MIN_SUMMARIES_PER_RUN}, Max={MAX_SUMMARIES_PER_RUN}")
    print(f"Hochwertige Dokumentation verfügbar unter:")
    print(f"  - Alle: {best_docs_dir}")
    print(f"  - Git-Repositories: {git_clones_dir}")
    print(f"  - Lokale Projekte: {local_projects_dir}")
    if ENABLE_SUMMARIZATION:
        print(f"  - KI-Zusammenfassungen: {summaries_dir}")
    print(f"==============================")
    
    # Create main index file
    with open(main_index_path, 'w', encoding='utf-8') as index_file:
        index_file.write(f"Hochwertige Projektdokumentation\n")
        index_file.write(f"Erstellt am: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        index_file.write(f"Git-Repositories: {git_projects}\n")
        index_file.write(f"Lokale Projekte: {local_dev_projects}\n\n")
        
        # List Git repositories
        index_file.write(f"=== Git-Repositories ===\n")
        git_zips = [f for f in os.listdir(git_clones_dir) if f.endswith('_dokumentation.zip')]
        for zip_name in sorted(git_zips):
            proj_name = zip_name.replace('_dokumentation.zip', '')
            index_file.write(f"- {proj_name}\n")
        
        # List local projects
        index_file.write(f"\n=== Lokale Projekte ===\n")
        local_zips = [f for f in os.listdir(local_projects_dir) if f.endswith('_dokumentation.zip')]
        for zip_name in sorted(local_zips):
            proj_name = zip_name.replace('_dokumentation.zip', '')
            index_file.write(f"- {proj_name}\n")
    
    # Create Git repositories index
    with open(git_index_path, 'w', encoding='utf-8') as index_file:
        index_file.write(f"Git-Repository Dokumentation\n")
        index_file.write(f"Erstellt am: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        git_zips = [f for f in os.listdir(git_clones_dir) if f.endswith('_dokumentation.zip')]
        for zip_name in sorted(git_zips):
            proj_name = zip_name.replace('_dokumentation.zip', '')
            index_file.write(f"- {proj_name}\n")
    
    # Create local projects index
    with open(local_index_path, 'w', encoding='utf-8') as index_file:
        index_file.write(f"Lokale Projekt-Dokumentation\n")
        index_file.write(f"Erstellt am: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
        
        local_zips = [f for f in os.listdir(local_projects_dir) if f.endswith('_dokumentation.zip')]
        for zip_name in sorted(local_zips):
            proj_name = zip_name.replace('_dokumentation.zip', '')
            index_file.write(f"- {proj_name}\n")
    
    print(f"Index-Dateien erstellt:")
    print(f"  - Hauptindex: {main_index_path}")
    print(f"  - Git-Repositories: {git_index_path}")
    print(f"  - Lokale Projekte: {local_index_path}")


if __name__ == "__main__":
    main()

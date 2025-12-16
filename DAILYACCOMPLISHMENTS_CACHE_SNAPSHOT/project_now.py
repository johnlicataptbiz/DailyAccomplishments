#!/usr/bin/env python3
import os
import shutil
import time
from pathlib import Path

DAYS = 30
DEST_ROOT = Path.home() / "Desktop" / "Project Now"

SCAN_ROOTS = [
    Path.home() / "Downloads",
    Path.home() / "Desktop",
    Path.home() / "Documents",
    Path.home() / "Pictures",
    Path.home() / "Movies",
    Path.home() / "Music",
]

DRY_RUN = True
DELETE_ORIGINALS = True

EXCLUDE_DIR_NAMES = {
    ".git", ".svn", ".hg",
    "node_modules", "__pycache__", ".DS_Store",
    "Library",
}

CATEGORIES = {
    "Documents": {".pdf", ".doc", ".docx", ".rtf", ".txt", ".md", ".pages", ".odt"},
    "Spreadsheets": {".xls", ".xlsx", ".csv", ".tsv", ".numbers"},
    "Presentations": {".ppt", ".pptx", ".key"},
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".tif", ".tiff", ".webp", ".heic", ".svg"},
    "Video": {".mp4", ".mov", ".mkv", ".avi", ".wmv", ".m4v"},
    "Audio": {".mp3", ".wav", ".m4a", ".aac", ".flac", ".ogg"},
    "Archives": {".zip", ".rar", ".7z", ".tar", ".gz", ".bz2"},
    "Code": {".py", ".js", ".ts", ".tsx", ".jsx", ".html", ".css", ".scss", ".json", ".yml", ".yaml",
             ".java", ".kt", ".go", ".rs", ".c", ".cpp", ".h", ".sh", ".ps1", ".sql", ".ipynb"},
    "Design": {".fig", ".sketch", ".xd"},
}

def category_for(path: Path) -> str:
    ext = path.suffix.lower()
    for cat, exts in CATEGORIES.items():
        if ext in exts:
            return cat
    return "Other"

def is_excluded_dir(p: Path) -> bool:
    return any(part in EXCLUDE_DIR_NAMES for part in p.parts)

def within_dest(p: Path) -> bool:
    try:
        p.resolve().relative_to(DEST_ROOT.resolve())
        return True
    except Exception:
        return False

def safe_copy(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dest)

def same_file_enough(src: Path, dest: Path) -> bool:
    return dest.exists() and src.exists() and src.stat().st_size == dest.stat().st_size

def prune_empty_dirs(start_dir: Path) -> None:
    for root, dirs, files in os.walk(start_dir, topdown=False):
        root_path = Path(root)
        if root_path == DEST_ROOT:
            continue
        if is_excluded_dir(root_path):
            continue
        try:
            if not any(root_path.iterdir()):
                if DRY_RUN:
                    print(f"[DRY] rmdir  {root_path}")
                else:
                    root_path.rmdir()
        except Exception:
            pass

def main():
    cutoff = time.time() - (DAYS * 24 * 60 * 60)
    DEST_ROOT.mkdir(parents=True, exist_ok=True)

    candidates = []
    for base in SCAN_ROOTS:
        if not base.exists():
            continue
        for root, dirs, files in os.walk(base):
            root_path = Path(root)

            if root_path == DEST_ROOT or within_dest(root_path):
                dirs[:] = []
                continue

            if is_excluded_dir(root_path):
                dirs[:] = []
                continue

            for name in files:
                src = root_path / name
                if src.is_symlink():
                    continue
                try:
                    st = src.stat()
                except Exception:
                    continue
                if st.st_mtime >= cutoff:
                    candidates.append(src)

    moved = 0
    for src in candidates:
        cat = category_for(src)

        rel_parent = None
        rel_root_name = "MiscRoot"
        for base in SCAN_ROOTS:
            try:
                rel_parent = src.resolve().relative_to(base.resolve()).parent
                rel_root_name = base.name
                break
            except Exception:
                continue

        if rel_parent is None:
            rel_parent = Path("")

        dest = DEST_ROOT / cat / rel_root_name / rel_parent / src.name

        if dest.exists():
            stem, suf = src.stem, src.suffix
            i = 2
            while True:
                candidate = dest.with_name(f"{stem} ({i}){suf}")
                if not candidate.exists():
                    dest = candidate
                    break
                i += 1

        if DRY_RUN:
            print(f"[DRY] copy   {src}  ->  {dest}")
        else:
            try:
                safe_copy(src, dest)
            except Exception as e:
                print(f"[WARN] copy failed: {src} ({e})")
                continue

        if DELETE_ORIGINALS:
            if DRY_RUN:
                print(f"[DRY] delete {src}")
            else:
                try:
                    if same_file_enough(src, dest):
                        src.unlink()
                    else:
                        print(f"[WARN] verification failed, not deleting: {src}")
                        continue
                except Exception as e:
                    print(f"[WARN] delete failed: {src} ({e})")
                    continue

        moved += 1

    if DELETE_ORIGINALS:
        for base in SCAN_ROOTS:
            if base.exists():
                prune_empty_dirs(base)

    print(f"\nDone. Processed {moved} files.")
    print(f"Destination: {DEST_ROOT}")
    if DRY_RUN:
        print("This was a DRY RUN. Set DRY_RUN = False to actually run it.")

if __name__ == "__main__":
    main()

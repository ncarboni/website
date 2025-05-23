#!/usr/bin/env python3
"""
PDF Thumbnail Generator for Jekyll Scholar
Generates thumbnails from PDFs and updates BibTeX with preview tags
"""

import os
import sys
import subprocess
import shutil
from pathlib import Path
import re
from typing import Dict, List, Tuple
import argparse

# Configuration
PDF_DIR = "assets/pdf"
THUMBNAIL_DIR = "assets/img/publication_preview"
BIB_FILE = "_bibliography/papers.bib"
THUMBNAIL_WIDTH = 1200
THUMBNAIL_HEIGHT = 1697  # A4 aspect ratio: 1200 * 1.414

# Colors for terminal output
class Colors:
    RED = '\033[0;31m'
    GREEN = '\033[0;32m'
    YELLOW = '\033[1;33m'
    BLUE = '\033[0;34m'
    NC = '\033[0m'  # No Color

def print_colored(text: str, color: str):
    """Print colored text to terminal"""
    print(f"{color}{text}{Colors.NC}")

def check_dependencies():
    """Check if required tools are available"""
    print_colored("=== Checking Dependencies ===", Colors.BLUE)
    
    # Check ImageMagick
    try:
        subprocess.run(['convert', '-version'], 
                      capture_output=True, check=True)
        print_colored("✅ ImageMagick found", Colors.GREEN)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print_colored("❌ ImageMagick not found. Please install ImageMagick.", Colors.RED)
        sys.exit(1)
    
    # Check Ghostscript
    try:
        subprocess.run(['gs', '--version'], 
                      capture_output=True, check=True)
        print_colored("✅ Ghostscript found", Colors.GREEN)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print_colored("❌ Ghostscript not found. Please install Ghostscript.", Colors.RED)
        sys.exit(1)

def check_directories():
    """Check and create necessary directories"""
    print_colored("\n=== Checking Directories ===", Colors.BLUE)
    
    if not Path(PDF_DIR).exists():
        print_colored(f"❌ PDF directory not found: {PDF_DIR}", Colors.RED)
        sys.exit(1)
    print_colored(f"✅ PDF directory found: {PDF_DIR}", Colors.GREEN)
    
    if not Path(BIB_FILE).exists():
        print_colored(f"❌ Bibliography file not found: {BIB_FILE}", Colors.RED)
        sys.exit(1)
    print_colored(f"✅ Bibliography file found: {BIB_FILE}", Colors.GREEN)
    
    # Create thumbnail directory if it doesn't exist
    Path(THUMBNAIL_DIR).mkdir(parents=True, exist_ok=True)
    print_colored(f"✅ Thumbnail directory ready: {THUMBNAIL_DIR}", Colors.GREEN)

def extract_pdf_files_from_bib() -> List[str]:
    """Extract PDF filenames from BibTeX file"""
    print_colored("\n=== Extracting PDF Files from Bibliography ===", Colors.BLUE)
    
    with open(BIB_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Find all PDF entries
    pdf_pattern = r'pdf\s*=\s*\{([^}]+)\}'
    pdf_files = re.findall(pdf_pattern, content, re.IGNORECASE)
    
    # Remove duplicates and sort
    pdf_files = sorted(list(set(pdf_files)))
    
    print_colored(f"Found {len(pdf_files)} PDF files in bibliography:", Colors.GREEN)
    for pdf_file in pdf_files[:5]:  # Show first 5
        print(f"  • {pdf_file}")
    if len(pdf_files) > 5:
        print(f"  ... and {len(pdf_files) - 5} more")
    
    return pdf_files

def generate_thumbnail(pdf_path: Path, thumbnail_path: Path) -> bool:
    """Generate thumbnail from PDF using ImageMagick"""
    try:
        cmd = [
            'convert',
            '-density', '150',
            f"{pdf_path}[0]",  # First page only
            '-colorspace', 'RGB',
            '-flatten',
            '-quality', '95',
            '-resize', f'{THUMBNAIL_WIDTH}x{THUMBNAIL_HEIGHT}',
            str(thumbnail_path)
        ]
        
        subprocess.run(cmd, capture_output=True, check=True)
        return True
    except subprocess.CalledProcessError as e:
        print_colored(f"    ❌ ImageMagick error: {e}", Colors.RED)
        return False

def process_thumbnails(pdf_files: List[str]) -> Dict[str, str]:
    """Generate thumbnails for PDF files"""
    print_colored("\n=== Generating Thumbnails ===", Colors.BLUE)
    
    processed = 0
    skipped = 0
    errors = 0
    thumbnail_map = {}  # pdf_filename -> thumbnail_filename
    
    for pdf_file in pdf_files:
        print_colored(f"\nProcessing: {pdf_file}", Colors.YELLOW)
        
        pdf_path = Path(PDF_DIR) / pdf_file
        thumbnail_name = pdf_file.replace('.pdf', '.jpg')
        thumbnail_path = Path(THUMBNAIL_DIR) / thumbnail_name
        
        # Check if PDF exists
        if not pdf_path.exists():
            print_colored(f"  ❌ PDF not found: {pdf_path}", Colors.RED)
            errors += 1
            continue
        
        # Check if thumbnail already exists
        if thumbnail_path.exists():
            print_colored(f"  ⏭️  Thumbnail already exists: {thumbnail_name}", Colors.YELLOW)
            skipped += 1
            thumbnail_map[pdf_file] = thumbnail_name
            continue
        
        # Generate thumbnail
        print_colored(f"  🔄 Generating thumbnail ({THUMBNAIL_WIDTH}x{THUMBNAIL_HEIGHT})...", Colors.YELLOW)
        if generate_thumbnail(pdf_path, thumbnail_path):
            print_colored(f"  ✅ Created: {thumbnail_name}", Colors.GREEN)
            processed += 1
            thumbnail_map[pdf_file] = thumbnail_name
        else:
            print_colored(f"  ❌ Failed to create thumbnail", Colors.RED)
            errors += 1
    
    print_colored(f"\n=== Thumbnail Generation Complete ===", Colors.BLUE)
    print_colored(f"✅ Thumbnails created: {processed}", Colors.GREEN)
    print_colored(f"⏭️  Thumbnails skipped: {skipped}", Colors.YELLOW)
    print_colored(f"❌ Errors: {errors}", Colors.RED)
    
    return thumbnail_map

def parse_bibtex_entries(content: str) -> List[Tuple[str, str, str]]:
    """
    Parse BibTeX content into entries
    Returns list of (entry_key, entry_header, entry_body) tuples
    """
    entries = []
    
    # Split by @ symbols that start new entries
    parts = re.split(r'(@\w+\s*\{[^,]+,)', content)
    
    # Skip first empty part, then process pairs
    for i in range(1, len(parts), 2):
        if i + 1 < len(parts):
            entry_header = parts[i].strip()
            entry_body = parts[i + 1]
            
            # Extract entry key
            key_match = re.search(r'@\w+\s*\{([^,]+),', entry_header)
            entry_key = key_match.group(1).strip() if key_match else f"entry_{i}"
            
            entries.append((entry_key, entry_header, entry_body))
        elif parts[i].strip():  # Handle last part if it exists
            entries.append((f"entry_{i}", parts[i], ""))
    
    return entries

def update_bibtex_with_previews(thumbnail_map: Dict[str, str]) -> None:
    """Update BibTeX file with preview tags"""
    print_colored("\n=== Updating BibTeX with Preview Tags ===", Colors.BLUE)
    
    # Create backup
    backup_file = f"{BIB_FILE}.backup"
    shutil.copy2(BIB_FILE, backup_file)
    print_colored(f"Backup created: {backup_file}", Colors.YELLOW)
    
    # Read current content
    with open(BIB_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Parse entries
    entries = parse_bibtex_entries(content)
    
    new_content = ""
    added_count = 0
    skipped_count = 0
    
    for entry_key, entry_header, entry_body in entries:
        # Check if entry already has preview tag
        if 'preview' in entry_body.lower() and '=' in entry_body:
            print_colored(f"  ⏭️  Entry '{entry_key}' already has preview tag", Colors.YELLOW)
            new_content += entry_header + entry_body
            skipped_count += 1
            continue
        
        # Look for PDF reference
        pdf_match = re.search(r'pdf\s*=\s*\{([^}]+)\}', entry_body, re.IGNORECASE)
        if pdf_match:
            pdf_filename = pdf_match.group(1)
            
            if pdf_filename in thumbnail_map:
                thumbnail_name = thumbnail_map[pdf_filename]
                print_colored(f"  ➕ Adding preview tag to '{entry_key}': {thumbnail_name}", Colors.GREEN)
                
                # Add preview tag before the PDF line
                pdf_line = pdf_match.group(0)
                preview_line = f"  preview = {{{thumbnail_name}}},"
                updated_body = entry_body.replace(pdf_line, f"{preview_line}\n  {pdf_line}")
                
                new_content += entry_header + updated_body
                added_count += 1
            else:
                new_content += entry_header + entry_body
        else:
            new_content += entry_header + entry_body
    
    # Write updated content
    with open(BIB_FILE, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print_colored(f"\n=== BibTeX Update Complete ===", Colors.BLUE)
    print_colored(f"✅ Preview tags added: {added_count}", Colors.GREEN)
    print_colored(f"⏭️  Entries skipped (already had preview): {skipped_count}", Colors.YELLOW)

def main():
    """Main function"""
    parser = argparse.ArgumentParser(description='Generate PDF thumbnails and update BibTeX')
    parser.add_argument('--thumbnails-only', action='store_true', 
                       help='Only generate thumbnails, do not update BibTeX')
    parser.add_argument('--bibtex-only', action='store_true',
                       help='Only update BibTeX with existing thumbnails')
    args = parser.parse_args()
    
    print_colored("=== PDF Thumbnail Generator for Jekyll Scholar ===", Colors.BLUE)
    
    # Check dependencies and directories
    check_dependencies()
    check_directories()
    
    # Extract PDF files from bibliography
    pdf_files = extract_pdf_files_from_bib()
    
    if not pdf_files:
        print_colored("No PDF files found in bibliography. Nothing to do.", Colors.YELLOW)
        return
    
    thumbnail_map = {}
    
    # Generate thumbnails (unless bibtex-only mode)
    if not args.bibtex_only:
        thumbnail_map = process_thumbnails(pdf_files)
    else:
        # In bibtex-only mode, find existing thumbnails
        for pdf_file in pdf_files:
            thumbnail_name = pdf_file.replace('.pdf', '.jpg')
            thumbnail_path = Path(THUMBNAIL_DIR) / thumbnail_name
            if thumbnail_path.exists():
                thumbnail_map[pdf_file] = thumbnail_name
    
    # Update BibTeX (unless thumbnails-only mode)
    if not args.thumbnails_only and thumbnail_map:
        update_bibtex_with_previews(thumbnail_map)
    
    print_colored("\n🎉 All done! Run 'bundle exec jekyll build' to see your thumbnails.", Colors.GREEN)

if __name__ == "__main__":
    main()
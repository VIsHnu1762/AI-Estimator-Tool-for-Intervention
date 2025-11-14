"""
File utility functions
"""
import hashlib
import uuid
from pathlib import Path
from datetime import datetime


def generate_unique_filename(original_filename: str) -> str:
    """
    Generate a unique filename while preserving the extension
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    unique_id = str(uuid.uuid4())[:8]
    
    # Get extension
    path = Path(original_filename)
    ext = path.suffix
    name = path.stem
    
    # Create unique filename
    safe_name = "".join(c for c in name if c.isalnum() or c in ('-', '_'))[:50]
    unique_filename = f"{safe_name}_{timestamp}_{unique_id}{ext}"
    
    return unique_filename


def compute_file_hash(file_path: str) -> str:
    """
    Compute SHA256 hash of a file
    """
    sha256_hash = hashlib.sha256()
    with open(file_path, "rb") as f:
        for byte_block in iter(lambda: f.read(4096), b""):
            sha256_hash.update(byte_block)
    return sha256_hash.hexdigest()

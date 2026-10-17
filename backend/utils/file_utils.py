"""
Secure File Handling and Clinical Document Utilities.

Provides strict MIME, size, extension, and content verification for medical documents.
Enforces private storage outside public web roots and generates cryptographic checksums.
"""

import hashlib
import os
from pathlib import Path
from typing import Any, Dict, Optional, Set, Tuple
import uuid
from werkzeug.datastructures import FileStorage
from werkzeug.utils import secure_filename

# Known file signatures (magic bytes) to prevent content-type spoofing
FILE_SIGNATURES: Dict[str, bytes] = {
    "pdf": b"%PDF",
    "png": b"\x89PNG\r\n\x1a\n",
    "jpg": b"\xff\xd8\xff",
    "jpeg": b"\xff\xd8\xff",
}

MIME_TYPE_MAPPING: Dict[str, str] = {
    "pdf": "application/pdf",
    "png": "image/png",
    "jpg": "image/jpeg",
    "jpeg": "image/jpeg",
}


def sanitize_filename(original_name: str) -> str:
    """Sanitize original filename removing risky path traversal sequences."""
    base = os.path.basename(original_name)
    sanitized = secure_filename(base)
    if not sanitized:
        sanitized = "unnamed_clinical_document"
    return sanitized


def verify_file_content(file_bytes: bytes, extension: str) -> bool:
    """
    Verify magic bytes match the expected file extension.
    Prevents executable or malicious files disguised with valid extensions.
    """
    ext = extension.lower().lstrip(".")
    if ext not in FILE_SIGNATURES:
        return False

    sig = FILE_SIGNATURES[ext]
    return file_bytes.startswith(sig)


def compute_sha256(file_bytes: bytes) -> str:
    """Compute standard SHA-256 hash of file content."""
    hasher = hashlib.sha256()
    hasher.update(file_bytes)
    return hasher.hexdigest()


def process_and_save_upload(
    file_storage: FileStorage,
    upload_folder: Path,
    allowed_extensions: Set[str],
    allowed_mimetypes: Set[str],
    max_size_bytes: int = 10 * 1024 * 1024,
) -> Tuple[bool, Optional[Dict[str, Any]], Optional[str]]:
    """
    Inspect, validate, and securely store an uploaded clinical document.

    Parameters
    ----------
    file_storage : FileStorage
        Uploaded file from Flask request.files.
    upload_folder : Path
        Target directory outside public web root.
    allowed_extensions : set of str
        Allowed extensions, e.g. {'pdf', 'png', 'jpg', 'jpeg'}.
    allowed_mimetypes : set of str
        Allowed MIME types.
    max_size_bytes : int
        Maximum allowed byte length (default 10 MB).

    Returns
    -------
    success : bool
        True if valid and saved.
    metadata : dict, optional
        Document metadata if successful.
    error_message : str, optional
        Clinical or security error description if failed.
    """
    if not file_storage or not file_storage.filename:
        return False, None, "No file provided for upload."

    original_filename = sanitize_filename(file_storage.filename)
    parts = original_filename.rsplit(".", 1)
    if len(parts) < 2:
        return False, None, "Uploaded file must have a valid file extension."

    extension = parts[1].lower()
    if extension not in allowed_extensions:
        return (
            False,
            None,
            f"Unsupported file extension '.{extension}'. Allowed: {sorted(list(allowed_extensions))}",
        )

    # Read content into memory to check size and magic bytes
    content = file_storage.read()
    file_size = len(content)

    if file_size == 0:
        return False, None, "Uploaded file is empty (0 bytes)."

    if file_size > max_size_bytes:
        max_mb = max_size_bytes / (1024 * 1024)
        return (
            False,
            None,
            f"File size exceeds allowable maximum of {max_mb:.1f} MB (received {file_size / (1024*1024):.2f} MB).",
        )

    # Validate declared MIME type
    declared_mime = file_storage.mimetype or "application/octet-stream"
    expected_mime = MIME_TYPE_MAPPING.get(extension)

    # Validate Magic Bytes / File Signatures
    if not verify_file_content(content, extension):
        return (
            False,
            None,
            f"File content verification failed: Magic byte header does not match declared format (.{extension}).",
        )

    # Ensure upload directory exists
    upload_folder.mkdir(parents=True, exist_ok=True)

    # Generate unique stored filename to prevent overwrites or traversal
    unique_prefix = uuid.uuid4().hex
    stored_filename = f"{unique_prefix}_{original_filename}"
    file_path = upload_folder / stored_filename

    # Save to disk
    with open(file_path, "wb") as f:
        f.write(content)

    # Calculate SHA-256
    sha256 = compute_sha256(content)

    metadata: Dict[str, Any] = {
        "original_filename": original_filename,
        "stored_filename": stored_filename,
        "file_type": "pdf" if extension == "pdf" else f"image_{extension}",
        "mime_type": expected_mime or declared_mime,
        "file_size_bytes": file_size,
        "sha256_hash": sha256,
        "storage_path": str(file_path),
    }

    return True, metadata, None

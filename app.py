"""
Flask File Storage Demo
========================
A small proof-of-concept showing how a single storage interface can
back onto either local disk (development) or Cloudflare R2 (production).

Endpoints:
    GET  /                  – Serve the upload page
    GET  /api/files         – List all uploaded files (JSON)
    POST /api/upload        – Upload a file
    GET  /api/files/<id>    – Download / redirect to a single file
    DELETE /api/files/<id>  – Delete a file
"""

import os
from dotenv import load_dotenv

# Load .env BEFORE any other imports that read env vars
load_dotenv()

from flask import (
    Flask,
    request,
    jsonify,
    render_template,
    send_from_directory,
    redirect,
)
from flask_cors import CORS
from storage import get_storage

# ──────────────────────────────────────────────
# App setup
# ──────────────────────────────────────────────

app = Flask(__name__)
CORS(app)

# Maximum upload size: 16 MB
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16 MB

# ──────────────────────────────────────────────
# Allowed file types
# ──────────────────────────────────────────────

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}

DOCUMENT_EXTENSIONS = {".pdf", ".txt", ".csv", ".zip", ".doc", ".docx"}

ALLOWED_EXTENSIONS = IMAGE_EXTENSIONS | DOCUMENT_EXTENSIONS


def _classify(filename):
    """
    Decide whether a file is an 'image' or a 'document'
    based on its extension.

    Returns:
        ("images", ext) or ("files", ext)
        or (None, None) if the extension is not allowed.
    """
    _, ext = os.path.splitext(filename)
    ext = ext.lower()
    if ext in IMAGE_EXTENSIONS:
        return "images", ext
    elif ext in DOCUMENT_EXTENSIONS:
        return "files", ext
    return None, None


# ──────────────────────────────────────────────
# Instantiate the storage backend
# ──────────────────────────────────────────────

storage = get_storage()

# ──────────────────────────────────────────────
# Routes
# ──────────────────────────────────────────────


@app.route("/")
def index():
    """Serve the single-page upload UI."""
    storage_type = os.getenv("STORAGE_TYPE", "local")
    return render_template("index.html", storage_type=storage_type)


@app.route("/uploads/<path:filepath>")
def serve_upload(filepath):
    """
    Serve locally-stored files.
    Only used when STORAGE_TYPE=local.
    """
    upload_folder = os.getenv("UPLOAD_FOLDER", "uploads")
    directory = os.path.join(os.getcwd(), upload_folder)
    return send_from_directory(directory, filepath)


# ──────────────────────────────────────────────
# API — list files
# ──────────────────────────────────────────────


@app.route("/api/files", methods=["GET"])
def api_list_files():
    """Return JSON array of all uploaded files."""
    try:
        files = storage.list_files()
        return jsonify({"success": True, "files": files})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ──────────────────────────────────────────────
# API — upload
# ──────────────────────────────────────────────


@app.route("/api/upload", methods=["POST"])
def api_upload():
    """Handle a file upload."""

    # 1. Check that a file was actually sent
    if "file" not in request.files:
        return jsonify({"success": False, "error": "No file provided."}), 400

    file = request.files["file"]

    if file.filename == "" or file.filename is None:
        return jsonify({"success": False, "error": "No file selected."}), 400

    # 2. Validate extension
    category, ext = _classify(file.filename)
    if category is None:
        return (
            jsonify(
                {
                    "success": False,
                    "error": (
                        f"File type '{ext or 'unknown'}' is not allowed. "
                        f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
                    ),
                }
            ),
            400,
        )

    # 3. Upload via the storage abstraction
    try:
        metadata = storage.upload_file(file, file.filename, category)
        return jsonify({"success": True, "file": metadata}), 201
    except Exception as e:
        return (
            jsonify({"success": False, "error": f"Upload failed: {e}"}),
            500,
        )


# ──────────────────────────────────────────────
# API — get / download a single file
# ──────────────────────────────────────────────


@app.route("/api/files/<file_id>", methods=["GET"])
def api_get_file(file_id):
    """Download or redirect to a single file."""
    metadata = storage.get_file(file_id)
    if not metadata:
        return jsonify({"success": False, "error": "File not found."}), 404

    # For local storage, serve the file directly
    directory, filename = storage.get_file_path(file_id)
    if directory and filename:
        return send_from_directory(directory, filename)

    # For R2, redirect to the public URL
    return redirect(metadata["url"])


# ──────────────────────────────────────────────
# API — delete
# ──────────────────────────────────────────────


@app.route("/api/files/<file_id>", methods=["DELETE"])
def api_delete_file(file_id):
    """Delete a file from storage."""
    try:
        deleted = storage.delete_file(file_id)
        if not deleted:
            return (
                jsonify({"success": False, "error": "File not found."}),
                404,
            )
        return jsonify({"success": True, "message": "File deleted."})
    except Exception as e:
        return (
            jsonify({"success": False, "error": f"Delete failed: {e}"}),
            500,
        )


# ──────────────────────────────────────────────
# Error handlers
# ──────────────────────────────────────────────


@app.errorhandler(413)
def request_entity_too_large(error):
    """Triggered when a file exceeds MAX_CONTENT_LENGTH."""
    return (
        jsonify(
            {
                "success": False,
                "error": "File is too large. Maximum size is 16 MB.",
            }
        ),
        413,
    )


@app.errorhandler(404)
def not_found(error):
    return jsonify({"success": False, "error": "Resource not found."}), 404


@app.errorhandler(500)
def internal_error(error):
    return jsonify({"success": False, "error": "Internal server error."}), 500


# ──────────────────────────────────────────────
# Run
# ──────────────────────────────────────────────

if __name__ == "__main__":
    app.run(debug=True, port=5000)

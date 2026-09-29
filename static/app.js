/**
 * File Storage Demo – Client-side JavaScript
 * ============================================
 * Handles file selection, upload, listing, and deletion
 * via the Flask JSON API.
 */

// ── DOM References ──────────────────────────────
const dropArea       = document.getElementById("drop-area");
const fileInput      = document.getElementById("file-input");
const selectedInfo   = document.getElementById("selected-info");
const selectedName   = document.getElementById("selected-name");
const selectedSize   = document.getElementById("selected-size");
const clearBtn       = document.getElementById("clear-selected");
const uploadBtn      = document.getElementById("upload-btn");
const uploadBtnText  = document.getElementById("upload-btn-text");
const progressWrap   = document.getElementById("progress-container");
const progressFill   = document.getElementById("progress-fill");
const progressText   = document.getElementById("progress-text");
const fileGrid       = document.getElementById("file-grid");
const fileCount      = document.getElementById("file-count");
const toastContainer = document.getElementById("toast-container");

// ── Constants ───────────────────────────────────
const MAX_SIZE = 16 * 1024 * 1024; // 16 MB

const ALLOWED_EXTENSIONS = [
  ".jpg", ".jpeg", ".png", ".webp", ".gif",
  ".pdf", ".txt", ".csv", ".zip", ".doc", ".docx",
];

const IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp", ".gif"];

/** Map file extensions to emoji icons for non-image files */
const FILE_ICONS = {
  ".pdf": "📄",
  ".txt": "📝",
  ".csv": "📊",
  ".zip": "📦",
  ".doc": "📃",
  ".docx": "📃",
};

// ── State ───────────────────────────────────────
let selectedFile = null;

// ── Init ────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  loadFiles();
  setupDragDrop();
});

// ── Drag & Drop ─────────────────────────────────

function setupDragDrop() {
  ["dragenter", "dragover"].forEach((evt) => {
    dropArea.addEventListener(evt, (e) => {
      e.preventDefault();
      dropArea.classList.add("upload-area--dragover");
    });
  });

  ["dragleave", "drop"].forEach((evt) => {
    dropArea.addEventListener(evt, (e) => {
      e.preventDefault();
      dropArea.classList.remove("upload-area--dragover");
    });
  });

  dropArea.addEventListener("drop", (e) => {
    const files = e.dataTransfer.files;
    if (files.length > 0) {
      handleFileSelect(files[0]);
    }
  });

  dropArea.addEventListener("click", () => fileInput.click());

  fileInput.addEventListener("change", () => {
    if (fileInput.files.length > 0) {
      handleFileSelect(fileInput.files[0]);
    }
  });

  clearBtn.addEventListener("click", (e) => {
    e.stopPropagation();
    clearSelection();
  });
}

// ── File Selection ──────────────────────────────

function handleFileSelect(file) {
  // Validate extension
  const ext = getExtension(file.name);
  if (!ALLOWED_EXTENSIONS.includes(ext)) {
    showToast(`File type "${ext}" is not allowed.`, "error");
    return;
  }

  // Validate size
  if (file.size > MAX_SIZE) {
    showToast("File is too large. Maximum size is 16 MB.", "error");
    return;
  }

  selectedFile = file;
  selectedName.textContent = file.name;
  selectedSize.textContent = formatSize(file.size);
  selectedInfo.classList.add("show");
  uploadBtn.disabled = false;
}

function clearSelection() {
  selectedFile = null;
  fileInput.value = "";
  selectedInfo.classList.remove("show");
  uploadBtn.disabled = true;
}

// ── Upload ──────────────────────────────────────

uploadBtn.addEventListener("click", uploadFile);

async function uploadFile() {
  if (!selectedFile) return;

  // UI: show progress
  uploadBtn.disabled = true;
  uploadBtn.classList.add("upload-btn--uploading");
  uploadBtnText.textContent = "Uploading…";
  progressWrap.classList.add("show");
  progressFill.style.width = "0%";
  progressText.textContent = "Starting upload…";

  const formData = new FormData();
  formData.append("file", selectedFile);

  try {
    // Use XMLHttpRequest for upload-progress events
    const result = await uploadWithProgress(formData);

    if (result.success) {
      showToast("File uploaded successfully!", "success");
      clearSelection();
      loadFiles(); // refresh the list
    } else {
      showToast(result.error || "Upload failed.", "error");
    }
  } catch (err) {
    showToast("Upload failed. Please try again.", "error");
  } finally {
    uploadBtn.disabled = false;
    uploadBtn.classList.remove("upload-btn--uploading");
    uploadBtnText.textContent = "Upload";
    progressWrap.classList.remove("show");
  }
}

function uploadWithProgress(formData) {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();

    xhr.upload.addEventListener("progress", (e) => {
      if (e.lengthComputable) {
        const pct = Math.round((e.loaded / e.total) * 100);
        progressFill.style.width = pct + "%";
        progressText.textContent = `${pct}% — ${formatSize(e.loaded)} / ${formatSize(e.total)}`;
      }
    });

    xhr.addEventListener("load", () => {
      try {
        resolve(JSON.parse(xhr.responseText));
      } catch {
        reject(new Error("Invalid response"));
      }
    });

    xhr.addEventListener("error", () => reject(new Error("Network error")));
    xhr.addEventListener("abort", () => reject(new Error("Upload aborted")));

    xhr.open("POST", "/api/upload");
    xhr.send(formData);
  });
}

// ── File List ───────────────────────────────────

async function loadFiles() {
  try {
    const res = await fetch("/api/files");
    const data = await res.json();

    if (!data.success) {
      showToast(data.error || "Failed to load files.", "error");
      return;
    }

    renderFiles(data.files);
  } catch {
    showToast("Could not load files.", "error");
  }
}

function renderFiles(files) {
  fileCount.textContent = files.length;

  if (files.length === 0) {
    fileGrid.innerHTML = `
      <div class="empty-state">
        <div class="empty-state__icon">📂</div>
        <p class="empty-state__text">No files uploaded yet. Drop a file above to get started.</p>
      </div>`;
    return;
  }

  fileGrid.innerHTML = files.map((f) => fileCardHTML(f)).join("");
}

function fileCardHTML(f) {
  const isImage = IMAGE_EXTENSIONS.includes(f.extension);
  const storageLabel = f.storage_type === "supabase" ? "Supabase Storage" : "Local Storage";
  const date = new Date(f.uploaded_at).toLocaleDateString(undefined, {
    year: "numeric", month: "short", day: "numeric",
  });

  // Thumbnail or icon
  let visual;
  if (isImage) {
    visual = `<img class="file-card__thumb" src="${escapeAttr(f.url)}" alt="${escapeAttr(f.original_name)}" loading="lazy">`;
  } else {
    const icon = FILE_ICONS[f.extension] || "📄";
    visual = `<div class="file-card__icon">${icon}</div>`;
  }

  // View vs Download label
  const actionLabel = isImage ? "View" : "Download";

  return `
    <div class="file-card" data-id="${f.id}">
      ${visual}
      <div class="file-card__info">
        <div class="file-card__name" title="${escapeAttr(f.original_name)}">${escapeHTML(f.original_name)}</div>
        <div class="file-card__meta">
          <span>📐 ${formatSize(f.size)}</span>
          <span>🗄️ ${storageLabel}</span>
          <span>📅 ${date}</span>
        </div>
        <div class="file-card__actions">
          <a class="btn-sm" href="${escapeAttr(f.url)}" target="_blank" rel="noopener">
            ${actionLabel}
          </a>
          <button class="btn-sm btn-sm--danger" onclick="deleteFile('${f.id}')">
            Delete
          </button>
        </div>
      </div>
    </div>`;
}

// ── Delete ──────────────────────────────────────

async function deleteFile(fileId) {
  if (!confirm("Delete this file?")) return;

  try {
    const res = await fetch(`/api/files/${fileId}`, { method: "DELETE" });
    const data = await res.json();

    if (data.success) {
      showToast("File deleted.", "success");

      // Animate removal
      const card = document.querySelector(`.file-card[data-id="${fileId}"]`);
      if (card) {
        card.style.transition = "opacity 0.3s, transform 0.3s";
        card.style.opacity = "0";
        card.style.transform = "translateY(-10px)";
        setTimeout(() => loadFiles(), 300);
      } else {
        loadFiles();
      }
    } else {
      showToast(data.error || "Delete failed.", "error");
    }
  } catch {
    showToast("Could not delete file.", "error");
  }
}

// ── Toast Notifications ─────────────────────────

function showToast(message, type = "success") {
  const toast = document.createElement("div");
  toast.className = `toast toast--${type}`;
  toast.textContent = message;
  toastContainer.appendChild(toast);

  setTimeout(() => {
    toast.classList.add("toast--removing");
    toast.addEventListener("animationend", () => toast.remove());
  }, 3500);
}

// ── Helpers ─────────────────────────────────────

function getExtension(filename) {
  const dot = filename.lastIndexOf(".");
  return dot !== -1 ? filename.slice(dot).toLowerCase() : "";
}

function formatSize(bytes) {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / (1024 * 1024)).toFixed(1) + " MB";
}

function escapeHTML(str) {
  const el = document.createElement("span");
  el.textContent = str;
  return el.innerHTML;
}

function escapeAttr(str) {
  return str.replace(/&/g, "&amp;").replace(/"/g, "&quot;").replace(/'/g, "&#39;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
}

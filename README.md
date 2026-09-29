# Flask File Storage Demo

A small proof-of-concept that demonstrates how a **single storage interface** can back onto either **local disk** (during development) or **Supabase Storage** (in production) — without changing any application code.

```
Upload  →  Storage Abstraction  →  Local / Supabase  →  View  →  Delete
```

---

## Features

- Upload images and documents via drag-and-drop or file picker
- Thumbnail previews for images
- View / download uploaded files
- Delete files
- Real-time upload progress bar
- Toast notifications for success and error states
- Automatic unique filenames (UUID) to prevent collisions
- File type and size validation (16 MB limit)

---

## Project Structure

```
flask-file-storage-demo/
│
├── app.py                      ← Flask application & API routes
├── requirements.txt            ← Python dependencies
├── .env                        ← Environment config (not committed)
├── .env.example                ← Template for .env
├── .gitignore
│
├── storage/
│   ├── __init__.py             ← get_storage() factory
│   ├── local_storage.py        ← Saves files to /uploads
│   └── supabase_storage.py     ← Uploads files to Supabase Storage
│
├── uploads/
│   ├── images/                 ← Local image storage
│   └── files/                  ← Local document storage
│
├── templates/
│   └── index.html              ← Upload page (Jinja2)
│
└── static/
    ├── style.css               ← Stylesheet
    └── app.js                  ← Client-side JavaScript
```

---

## 1. Local Development

### Prerequisites

- Python 3.9 or newer

### Setup

```bash
# Clone / navigate to the project
cd flask-file-storage-demo

# Create a virtual environment
python -m venv venv

# Activate it
# Windows:
venv\Scripts\activate
# macOS / Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Configure

Copy the example env file and edit if needed:

```bash
cp .env.example .env
```

The defaults are already set for local development:

```env
STORAGE_TYPE=local
UPLOAD_FOLDER=uploads
```

### Run

```bash
python app.py
```

Open [http://localhost:5000](http://localhost:5000) in your browser.

Uploaded files will be saved to:

```
uploads/images/   ← image files
uploads/files/    ← documents
```

---

## 2. Supabase Storage Configuration

### Create a Supabase Project

1. Go to [supabase.com](https://supabase.com/) and sign in.
2. Click **New Project** and give it a name.
3. Wait for the project to finish provisioning.

### Create a Storage Bucket

1. In your project dashboard, navigate to **Storage** in the sidebar.
2. Click **New Bucket**.
3. Name it (e.g. `uploads`).
4. Toggle **Public bucket** to ON if you want files to be publicly accessible.
5. Click **Create bucket**.

### Get Your Credentials

1. Go to **Project Settings** → **API**.
2. Copy your **Project URL** — this is `SUPABASE_URL`.
3. Under **Project API keys**, copy the `service_role` key — this is `SUPABASE_KEY`.
   - Use the **service_role** key (not the `anon` key) for server-side uploads so that RLS policies don't block your backend.

### (Optional) Configure RLS Policies

If your bucket is **public**, no additional policies are needed for reading.

For uploads and deletes, the `service_role` key bypasses RLS, so no policies are required on the backend.

### Update `.env`

```env
STORAGE_TYPE=supabase

SUPABASE_URL=https://xyzcompany.supabase.co
SUPABASE_KEY=your_service_role_key
SUPABASE_BUCKET=uploads
```

Restart the application — uploads will now go to Supabase Storage.

---

## 3. Switching Storage Providers

The entire switch is controlled by **one environment variable**:

| Environment | `.env` setting | Files stored in |
|-------------|----------------|-----------------|
| Development | `STORAGE_TYPE=local` | `uploads/` folder on disk |
| Production  | `STORAGE_TYPE=supabase` | Supabase Storage bucket |

**No application code changes are required.** The `get_storage()` factory in [`storage/__init__.py`](storage/__init__.py) reads `STORAGE_TYPE` and returns the correct backend. Both backends expose the same API:

```python
storage = get_storage()

storage.upload_file(file, filename, category)
storage.list_files()
storage.get_file(file_id)
storage.delete_file(file_id)
```

---

## Allowed File Types

### Images
`.jpg` `.jpeg` `.png` `.webp` `.gif`

### Documents
`.pdf` `.txt` `.csv` `.zip` `.doc` `.docx`

Maximum upload size: **16 MB**

---

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Serve the upload page |
| `GET` | `/api/files` | List all uploaded files (JSON) |
| `POST` | `/api/upload` | Upload a file |
| `GET` | `/api/files/<id>` | Download / view a file |
| `DELETE` | `/api/files/<id>` | Delete a file |

---

## License

This is a demo project for educational purposes.

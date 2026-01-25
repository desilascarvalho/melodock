# 🎧 Melodock

[![Buy Me a Coffee](https://img.shields.io/badge/☕_Buy_me_a_coffee-Support-yellow)](https://buymeacoffee.com/desilascarvalho)

> **Melodock** is a self-hosted music manager and downloader powered by **Deemix**.
> It downloads high-quality audio (FLAC / MP3 320kbps) directly from Deezer servers, offering a beautiful, organized local library with perfect metadata.

![Python](https://img.shields.io/badge/Python-3.10-blue?style=flat\&logo=python)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat\&logo=docker)
![Deemix](https://img.shields.io/badge/Engine-Deemix-orange)
![Status](https://img.shields.io/badge/Status-v5.2-success)

---

## ✨ Features

* **💎 Hi-Fi Quality:** Native Deezer downloads. Supports **FLAC (Lossless)**, MP3 320kbps, and 128kbps.
* **🛡️ Stealth Mode (Anti-Ban):** Advanced queuing algorithm that simulates human behavior (random pauses, session breaks) to protect your ARL account.
* **🧹 Smart Filters:** Automatically ignores Karaoke, Playbacks, Instrumentals, and large Compilations/Anthologies.
* **🏷️ Perfect Metadata:** Official metadata with cover art, artist, year, genre, and track number.
* **📂 Plex / Jellyfin Friendly:** Clean structure (`/Artist/Album/Track.mp3`) with proper handling of featured artists.
* **🔄 Smart Import:** Scans your existing `/music` folder and links files without re-downloading.
* **📊 Visual Dashboard:** Modern dark-mode interface to manage downloads and settings.

---

## 🚀 How to Run (Quick Start)

### 🔑 Prerequisites

* A **Deezer ARL Cookie** (authentication token)
* How to get it:
  `Deezer.com → F12 (DevTools) → Application → Cookies → arl`

---

## ▶️ Option 1: Docker Compose (Recommended)

Create a `docker-compose.yml` file:

```yaml
----------------------------------
services:
  melodock:
    image: desilascarvalho/melodock:latest
    container_name: melodock
    ports:
      - "9014:9014"
    volumes:
      - ./music:/music          # Final library storage
      - ./downloads:/downloads  # Temporary download folder
      - ./config:/config        # Database and cache
    restart: unless-stopped
```

Run it:

```bash
docker-compose up -d
```

---

## ▶️ Option 2: Docker CLI

```bash
docker run -d \
  --name melodock \
  -p 9014:9014 \
  -v /path/to/your/music:/music \
  -v /path/to/your/downloads:/downloads \
  -v /path/to/your/config:/config \
  --restart unless-stopped \
  desilascarvalho/melodock:latest
```

---

## ⚙️ Configuration

1. Access the interface:

   ```
   http://localhost:9014
   ```
2. Open **Config / Settings**
3. Paste your **ARL token**
4. Select download quality (**MP3 320kbps** or **FLAC**)
5. (Optional) Adjust filters (e.g. `live`, `remix`, `karaoke`)

---

## 📂 Volumes Explained

| Container Path | Description                                |
| -------------- | ------------------------------------------ |
| `/music`       | Final organized music library              |
| `/downloads`   | Temporary processing folder                |
| `/config`      | Database (`melodock.db`) and artist images |

---

## 🤝 Contributing

Contributions are welcome!

```bash
# Fork the project on GitHub

# Create a feature branch
git checkout -b feature/AmazingFeature

# Commit your changes
git add .
git commit -m "Add some AmazingFeature"

# Push your branch
git push origin feature/AmazingFeature
```

Then open a **Pull Request** 🚀

---

## ☕ Buy Me a Coffee

Maintaining **Melodock** takes time and coffee ☕🙂

I’m just a guy trying to build things and learn as I go.
If this project helped you in any way:

* ☕ [Buy me a coffee](https://buymeacoffee.com/desilascarvalho)
* ⭐ Star the repository
* 🤝 Share the project

Every bit of support is truly appreciated ❤️

---

## 📝 License

Distributed under the **MIT License**.
See the `LICENSE` file for more information.

---
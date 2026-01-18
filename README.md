# 🎧 Melodock

> **Melodock** is a self-hosted music manager and downloader. It combines metadata organization from streaming services with YouTube downloads, offering a beautiful, organized local library with automatic tagging.

![Python](https://img.shields.io/badge/Python-3.10-blue?style=flat\&logo=python)
![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat\&logo=docker)
![Status](https://img.shields.io/badge/Status-Active-success)

---

## ✨ Features

* **🔍 Smart Search:** Search artists and albums using Deezer API for accurate metadata.
* **📥 Auto Download:** Downloads tracks in high quality using `yt-dlp` and converts to MP3 (192kbps/320kbps).
* **🏷️ Auto Tagging:** Automatically applies cover art, artist, year, and genre (ID3 Tags).
* **📂 File Organization:** Automatically creates folder structure `/Artist/Album/Track.mp3`.
* **📊 Visual Dashboard:** Modern Dark Mode interface to manage your library.
* **🔄 Auto-Healing:** Automatically fetches artist images and fixes metadata.
* **🐳 Dockerized:** Easy to install and run anywhere.

---

## 🚀 How to Run (Quick Start)

You don’t need to build the code from source if you just want to use the app.
You can pull the official image directly from Docker Hub.

---

## ▶️ Option 1: Docker CLI (Terminal)

📋 **Copy & Paste**

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

ℹ️ Replace `/path/to/your/...` with the actual paths on your machine.

---

## ▶️ Option 2: Docker Compose / Portainer Stack

📋 **docker-compose.yml**

```yaml
version: '3.8'

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

🌐 Access the interface:

```text
http://localhost:9014
```

---

## 🛠️ Building from Source (Development)

Use this only if you want to modify the code or build your own image.

### 📥 Clone the repository

```bash
git clone https://github.com/YOUR_USERNAME/melodock.git
cd melodock
```

### 🏗️ Build the image

```bash
chmod +x build.sh
./build.sh
```

### ▶️ Run with Docker Compose

```bash
docker-compose up -d
```

---

## ⚙️ Volumes Explained

| Container Path | Description                                |
| -------------- | ------------------------------------------ |
| `/music`       | Final organized music library              |
| `/downloads`   | Temporary download processing folder       |
| `/config`      | Database (`melodock.db`) and artist images |

---

## 🤝 Contributing

📋 **Workflow**

```bash
# Fork the project
git checkout -b feature/AmazingFeature

# Commit your changes
git commit -m "Add some AmazingFeature"

# Push to your branch
git push origin feature/AmazingFeature
```

Then open a **Pull Request** 🚀

---

## 📝 License

Distributed under the **MIT License**.
See the `LICENSE` file for more information.

---
## 🎨 v5.2.8: Visual Upgrade & Plex Fixes

This update focuses on UI improvements and metadata handling for better media server compatibility (Plex/Jellyfin).

### ✨ Visual Improvements
- **Circular Artist Design:** The library dashboard now features modern, circular artist cards.
- **Real Artist Images:** The system now correctly downloads and displays artist profile pictures in the dashboard instead of color gradients.
- **Improved Fallback:** If an image is missing, a stylized gradient with the artist's initial is shown.

### 🏷️ Metadata & Plex Fixes
- **Feat. Handling:** Artists featured on a track are now moved to the **Title** tag (e.g., "Song Name (feat. Guest)").
- **Clean Artist Tag:** The "Artist" tag now contains *only* the main artist name. This prevents Plex from creating split entries like "Main Artist; Guest Artist".
- **Strict Album Artist:** Forces the "Album Artist" tag to match the database artist name.

### 🐛 Bug Fixes
- Fixed `save_artist_image` function which was previously a placeholder, ensuring images are now saved to `/config`.
- Improved Deemix configuration for cleaner ID3 tags.

### ⚙️ How to Apply
1. Update the container.
2. Go to **Config** > **Importar** > **Iniciar Scan** (to link existing artists and download their images).
3. New downloads will automatically have the corrected tags.
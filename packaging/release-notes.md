## v0.2.6 değişiklikleri

- Kodlama ajanında proje bazında kaydedilen model seçimi; devam eden sohbetlerde yeni modelle devam etme.
- Eklenen, değişen ve silinen dosyalar için otomatik yenilenen, renkli önce/sonra fark görünümü.
- Komutları, araç parametrelerini, çıktıları, süreleri ve hataları gösteren canlı işlem kaydı.
- Alt klasörlerdeki kaynak dosyaların listesi ve satır numaralı dosya önizlemesi.
- Projeyi ve seçili dosyayı VS Code, Cursor, Zed veya özel editörde açma; editör tercihini kaydetme.
- Küçük pencerelerde fark görünümünü kullanılabilir tutan kompakt yerleşim.

## Masaüstü kurulumu

- **Windows x64:** `windows-x64-setup.exe` dosyasını açın. Kullanıcı hesabınıza kurulur; Python gerekmez. ZIP taşınabilir sürümdür.
- **macOS Apple Silicon:** `macos-arm64.dmg` dosyasını açıp evren'i Applications'a sürükleyin.
- **macOS Intel:** `macos-x64.dmg` dosyasını kullanın. macOS paketleri macOS 15 ve üzeri için derlenir.
- **Ubuntu 22.04+ / Debian 12+:** `sudo apt install ./evren_*_amd64.deb`
- **Fedora / openSUSE:** `.rpm` paketini dağıtımınızın paket yöneticisiyle kurun. glibc 2.35+ ve x86_64 gerekir.
- **Diğer glibc tabanlı Linux dağıtımları:** `linux-x86_64.tar.gz` arşivini açıp `usr/bin/evren` dosyasını çalıştırın. X11/XWayland ve glibc 2.35+ gerekir. Alpine/musl desteklenmez.

Linux'ta API anahtarını kaydetmek için çalışan bir Secret Service anahtarlığı (ör. GNOME Keyring veya uyumlu KWallet) gerekir.

Bu sürümün macOS ve Windows paketleri geliştirici sertifikasıyla imzalanmamıştır; macOS Gatekeeper / Windows SmartScreen ek onay isteyebilir. Kurulum dosyaları için SHA256 özetleri `SHA256SUMS.txt` içindedir.

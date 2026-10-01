## v0.2.10 değişiklikleri

- Sohbet geçmişi aranabilir bir yan listeye taşındı; taslaklar ve kaydırma konumları korunur.
- Bir sohbet yanıt yazarken başka sohbetlerde soru sorulabilir; yanıtlar arka planda bağımsız devam eder.
- Yanıt yazılan ve yeni yanıt gelen sohbetler listede işaretlenir. Durdur düğmesi yalnızca seçili sohbeti durdurur.
- Akış sırasında ara kayıtlar ve sürekli “Kaydediliyor” göstergesi kaldırıldı. Yanıt tamamlandığında veya durdurulduğunda kayıt yapılır.
- Her sohbetin model, araç işleyicileri ve çalışma dizini ayrı tutulur; diğer sohbetlerin ayarlarıyla karışmaz.
- Computer-use MCP varsayılan olarak eklenir ve yeni sohbetlerde seçilir. Yerleşik sunucu harici Python gerektirmez; kapatma ve kaldırma tercihleri korunur.

## Masaüstü kurulumu

- **Windows x64:** `windows-x64-setup.exe` dosyasını açın. Kullanıcı hesabınıza kurulur; Python gerekmez. ZIP taşınabilir sürümdür.
- **macOS Apple Silicon:** `macos-arm64.dmg` dosyasını açıp evren'i Applications'a sürükleyin.
- **macOS Intel:** `macos-x64.dmg` dosyasını kullanın. macOS paketleri macOS 15 ve üzeri için derlenir.
- **Ubuntu 22.04+ / Debian 12+:** `sudo apt install ./evren_*_amd64.deb`
- **Fedora / openSUSE:** `.rpm` paketini dağıtımınızın paket yöneticisiyle kurun. glibc 2.35+ ve x86_64 gerekir.
- **Diğer glibc tabanlı Linux dağıtımları:** `linux-x86_64.tar.gz` arşivini açıp `usr/bin/evren` dosyasını çalıştırın. X11/XWayland ve glibc 2.35+ gerekir. Alpine/musl desteklenmez.

Linux'ta API anahtarını kaydetmek için çalışan bir Secret Service anahtarlığı (ör. GNOME Keyring veya uyumlu KWallet) gerekir.

Bu sürümün macOS ve Windows paketleri geliştirici sertifikasıyla imzalanmamıştır; macOS Gatekeeper / Windows SmartScreen ek onay isteyebilir. Kurulum dosyaları için SHA256 özetleri `SHA256SUMS.txt` içindedir.

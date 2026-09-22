# EVREN CLI

EVREN'in **LLM Çıkarım API'sini terminalden kullanmak** için CLI ve Python istemcisi. Sohbetin yanında görsel anlama, OCR, ses çözümleme, embeddings, rerank, medya yükleme, kota/kredi ve istek durumu sorgularını destekler. Önceki agent, MCP, skill ve plugin özellikleri `evren-agent` komutuyla kullanılmaya devam eder.

**Kapsam:** 22 Eylül 2026 tarihinde okunan [resmî OpenAPI şemasındaki](https://evren-llmapi.ssyz.org.tr/openapi.json) **20 genel işlemin tamamı**. `internal` servis uçları kapsam dışıdır. [Uç nokta ve kapsam tablosu](docs/API.md).

EVREN portalında **Platform**, **LLM Çıkarım** ve **Model Çıkarımı** farklı anahtar türleridir. Anahtar listesinde “Tümü” bir filtre, “Modeller: Tümü” ise LLM model yetkisidir. Bu istemci `evren_llm_...` biçimindeki **LLM Çıkarım** anahtarını kullanır. Veri seti/etiketleme, GPU rezervasyonu, eğitim işleri, organizasyon veya platform anahtarı yönetimi için doğrulanmış genel API sözleşmesi bulunamadığından bu işlemler eklenmemiştir. Portalın bütün MLOps özelliklerinin bu anahtarla kullanılabildiği varsayılmaz.

## Kurulum

Python 3.10+:

### ⚡ Tek Komutla Hızlı Kurulum (Otomatik .venv ve paketler)

İşletim sisteminize göre tek bir komut çalıştırmanız yeterlidir:

```bash
# macOS / Linux:
./install.sh
# veya
make install

# Windows (PowerShell):
.\install.ps1

# Tüm Sistemler (Evrensel Python):
python install.py
```

Kurulum betiği `uv` (varsa) veya Python'un yerleşik `venv` + `pip` modülünü kullanarak sanal ortamı kurar ve bağımlılıkları yükler. `.env` oluşturmaz; mevcut dosyanıza dokunmaz.

**Venv'i aktive etmeniz gerekmez.** Kurulum, `evren` ve `evren-agent` komutlarını macOS/Linux'ta `~/.local/bin`, Windows'ta `%LOCALAPPDATA%\EVREN\bin` üzerinden erişilebilir yapar ve kullanıcı PATH ayarını kaydeder. macOS/Linux'ta kullanılan kabuğun zsh, bash veya fish başlangıç dosyası güncellenir. Diğer kabuklarda `~/.profile` güncellenir; kabuğunuz bu dosyayı okumuyorsa PATH'i kendi başlangıç dosyanıza ekleyin.

İlk kurulumdan sonra **yeni bir terminal açın** veya kurulumun sonunda gösterilen PATH komutunu mevcut terminalde bir kez çalıştırın. Kurulum betiği, kendisini başlatan terminalin ortamını doğrudan değiştiremez. Sonrasında `evren --help` ve `evren-agent --commands` herhangi bir klasörden çalışır; bağımlılıklar projenin `.venv` ortamında kalır. Proje klasörünü veya `.venv` dizinini silmeyin; projeyi taşırsanız `.venv` ortamını yeniden oluşturup kurulumu tekrar çalıştırın. `config.yaml` gibi göreli dosya yolları komutu çalıştırdığınız klasöre göre değerlendirilir.

`install.sh` ve `install.ps1` aynı `install.py` kurulumunu çalıştırır; üç giriş noktası da aktivasyonsuz kullanımı ayarlar. Windows'ta `install.ps1` mevcut PowerShell oturumunun PATH'ini de yeniler; bu oturumda yeni terminal açmadan komutları kullanabilirsiniz.

<details>
<summary><b>Manuel Kurulum Adımları (İsteğe Bağlı)</b></summary>

```bash
# macOS / Linux (bash/zsh):
uv venv .venv
source .venv/bin/activate
uv pip install -e '.[dev]'

# Windows (PowerShell):
uv venv .venv
.\.venv\Scripts\Activate.ps1
uv pip install -e '.[dev]'

# Windows (Command Prompt - CMD):
uv venv .venv
.venv\Scripts\activate.bat
uv pip install -e '.[dev]'
```
</details>

Kurulumdan sonra `evren`, `evren-agent` veya anahtar gerektiren ilk komutu çalıştırın. Anahtar bulunamazsa terminalde **LLM Çıkarım** API anahtarınız gizli girişle sorulur. Anahtar proje dosyalarına yazılmaz; [keyring](https://keyring.readthedocs.io/en/latest/) aracılığıyla macOS Keychain, Windows Credential Locker veya Linux Secret Service/KWallet kasasında saklanır. Sonraki açılışlarda, farklı bir klasörden çalıştırsanız da otomatik okunur.

```bash
evren                              # İlk kurulum, ardından komut yardımı
evren login                        # Kaydedilmiş EVREN anahtarını değiştir
evren login --provider llmtr        # İsteğe bağlı diğer sağlayıcı
evren login --provider openai
```

Anahtarlar sağlayıcı, API adresi ve `api_key_env` adına göre ayrı saklanır. Özel bir adres için `evren login --base-url https://sunucunuz/v1` veya `--config DOSYA` kullanın. `login` anahtarı kaydeder; geçerliliğini API'de sorgulamaz. `evren models` ile bağlantıyı kontrol edebilirsiniz.

Mevcut ortam değişkenleri ve `.env` dosyaları geriye dönük uyumluluk için desteklenir ve kasadaki anahtardan önce gelir. Yeni kaydı kullanmak için eski ortam/`.env` değerini kaldırın. Şablon anahtarlar gerçek anahtar sayılmaz. `--help`, `--commands`, `api-docs`, `health` ve MCP yönetimi anahtar istemez. Terminal dışı çalıştırmalarda (pipe/CI) giriş beklenmez; kayıtlı anahtar veya ortam değişkeni yoksa açıklayıcı hata döner.

İşletim sistemi kasası kullanılamıyorsa otomatik kurulumda girilen anahtar yalnızca o çalıştırma boyunca bellekte tutulur ve bu durum bildirilir. `evren login` kalıcı kaydı tamamlayamazsa hata verir. Linux'ta etkin Secret Service/KWallet gerekir; dosyaya düz metin kaydetme alternatifi kullanılmaz.

Kimlik doğrulama ve anahtar oluşturma [EVREN portalında](https://evren.ssyz.org.tr/api-keys) yapılır. CLI e-Devlet şifresi istemez. Anahtar komut satırı argümanı olarak alınmaz.

## İlk kullanım

```bash
evren --help
evren health
evren health --ready
evren terms status
evren terms text --text
# Yalnızca okuduğunuz ve kabul etmek istediğiniz sürümü belirtin:
evren terms accept 1
evren models
evren quota
evren chat -p 'Merhaba!' --text
```

Şartlar otomatik kabul edilmez. `accept 1` yalnızca örnektir; güncel sürümü `terms text` ve `terms status` ile okuyun. Anahtarınız şartları zaten kabul etmişse tekrar kabul etmeniz gerekmez.

Yeni komutlar şu biçimlerde de çalışır:

```bash
evren-agent api models
python -m evren_agent.api.cli models
# Agent REPL içinde:
# /api models
# /api quota
# /api --help
```

## Komutlar

| Komut | İşlev |
|---|---|
| `models` | Erişilebilir modeller, görev, modalite ve güncel fiyat bilgisi |
| `chat` | Sohbet, görsel girdiler, araç çağrıları, yapılandırılmış çıktı, SSE |
| `completions` | Klasik metin tamamlama; tek/çoklu prompt ve SSE |
| `responses` | Responses API; yapılandırılmış girdi, araçlar ve türlenmiş SSE olayları |
| `embeddings` | Tek veya çoklu metnin vektör temsili |
| `rerank` | Sorguya göre belge sıralama |
| `ocr` | Görselden metin çıkarma |
| `transcribe` | Ses → metin, JSON, SRT, verbose/diarized JSON |
| `media upload` | Tek/çok parçalı yükleme ve tamamlama; isteğe bağlı finalize |
| `media initiate/status/complete/finalize/abort` | Medyanın bütün genel API işlemleri |
| `quota` | Token kullanımı, kota penceresi, yenilenme, rezerve/kalan kredi |
| `request-status ID` | İsteğin yürütme ve ücretlendirme durumu; eski yanıt gövdesini döndürmez |
| `terms status/text/accept` | Şartları okuma, durum ve açık sürüm kabulü |
| `health [--ready]` | Anahtarsız servis durumu |
| `request METHOD PATH` | Belgelenmiş uçlara tam JSON gönderme |
| `api-docs` | Çevrimdışı endpoint listesi, `--schema` ile OpenAPI sözleşmesi |

Her komutta `--help` bulunur. API komutları agent, plugin veya MCP sunucusu başlatmaz; LLMTR'ye otomatik yönlendirme yapmaz.

## Sohbet, görsel anlama ve akış

```bash
evren chat -m glm-5.3 -p 'Türkiye hakkında üç cümle yaz.' --text
evren chat -p 'Kısa bir öykü yaz.' --stream --text
evren chat -m qwen3-vl-30b --image ./foto.png -p 'Görseli açıkla.' --text
evren chat --system 'Kısa cevap ver.' --prompt @soru.txt --max-tokens 512
cat soru.txt | evren chat --prompt - --text

evren completions --prompt 'Bir zamanlar' --max-tokens 128
evren responses --prompt 'Bu konuyu açıkla' --stream
# Sunucu tarafında canlı veri araçlarına açık katılım:
evren chat -p 'Güncel bilgiyi kontrol et.' --evren-tools
```

`--image` tekrar edilebilir. `--image-url` uzak veya data URL girdileri içindir. Modellerin modaliteleri ve erişim durumu değişebilir; `evren models` yanıtını esas alın. `--evren-tools` sunucunun özelliğidir; model/gateway desteğini sunucu doğrular.

## Embeddings ve rerank

```bash
evren embeddings -m qwen3-embedding-8b --input 'Birinci metin' --input @belge.txt -o vectors.json
evren rerank -m qwen3-reranker-8b --query 'yapay zekâ' \
  --document 'Makine öğrenmesi üzerine bir belge' --document 'Bahçecilik rehberi'
evren rerank -m qwen3-reranker-8b --query 'arama metni' --documents @belgeler.json
```

`belgeler.json` bir metin dizisidir: `["Belge 1", "Belge 2"]`. Bu komutlarda `--model` veya JSON gövdesinde `model` gereklidir. Yukarıdaki modeller 22 Eylül 2026 canlı katalog kontrolünde görüldü; örnekler hesabınızın gelecekteki erişimini garanti etmez.

## OCR ve ses

```bash
evren ocr --file ./taranan.png --model dots-ocr --text -o metin.txt
evren ocr --file ./taranan.jpg --model deepseek-ocr-2
evren transcribe ./kayit.wav --language tr --response-format text -o kayit.txt
evren transcribe ./kayit.wav --response-format srt -o altyazi.srt
evren transcribe ./kayit.wav --response-format diarized_json -o konusmacilar.json
```

OCR görsel girdisini resmî `image` data URL alanına dönüştürür; PDF ayrıştırıcısı değildir. Ses dosyaları `multipart/form-data` gönderilir. Desteklenen ses çıktı seçenekleri: `json`, `text`, `srt`, `verbose_json`, `diarized_json`. Metin ve SRT çıktıları JSON tırnakları eklenmeden yazılır.

## Medya

```bash
evren media upload ./video.mp4
# Yükleme + complete + finalize:
evren media upload ./video.mp4 --finalize
# Yukarıdaki yanıttaki media_id değerini kullanın:
evren media status MEDIA_UUID
evren media finalize MEDIA_UUID
evren media abort MEDIA_UUID

# Yüklemeyi başka bir araçla yapmak için:
evren media initiate --content-type video/mp4 --size-bytes 123456
# İmzalı URL'lere PUT yaptıktan sonra:
evren media complete MEDIA_UUID
# Çok parçalı yüklemede her PUT yanıtının ETag değerini kullanın:
evren media complete MEDIA_UUID --parts @parts.json
```

`parts.json`: `[{"part_number":1,"etag":"\"storage-etag\""}]`.

`upload` sunucunun verdiği tek/çok parçalı planı izler; dosyayı belleğe bütünüyle almaz ve storage adresine EVREN anahtarı göndermez. Tamamlama öncesi hata veya iptalde `abort` dener. Finalize başarısızsa tamamlanmış medyayı otomatik silmez; durumunu kontrol edip finalize komutunu tekrar kullanabilirsiniz. `initiate` çıktısındaki imzalı URL'ler geçici yükleme yetkisi taşır.

## Tam API parametreleri ve otomasyon

`--body` inline JSON, `@dosya.json` veya stdin için `-` kabul eder. `--set ALAN=JSON` parametresi tekrar edilebilir; `tools`, `tool_choice`, `response_format`, `reasoning_effort`, `stop`, `seed`, `top_k` gibi ek alanlar korunur. CLI seçenekleri JSON gövdesindeki ilgili alanları geçersiz kılar; `messages` ile `--prompt/--image` çakışması hata verir.

```bash
evren chat --body @conversation.json --set 'reasoning_effort="high"'
evren responses --body @request.json -o response.json
evren request POST /v1/chat/completions --body @conversation.json
evren request GET /v1/quota --metadata
evren request-status REQUEST_UUID
evren api-docs --schema -o evren-openapi.json
evren api-docs --path /v1/media
```

`request` yalnızca kaydedilmiş genel uçlara erişir; `internal` servis yollarını veya başka siteleri kabul etmez. Yeni uç noktalar için şemanın ve kapsam testinin güncellenmesi gerekir. Ses için dosya seçeneği olan `transcribe` komutunu kullanın.

Varsayılan stdout çıktısı JSON'dur. `--text` metin çıktısını seçer. Akışta varsayılan çıktı her satırda `{ "event": ..., "data": ... }` içeren **JSONL**'dır; reasoning, usage, tool-call ve Responses olayları korunur. `--stream --text` yalnızca metin deltalarını gösterir; araç çağrısı işlemek isteyenler JSONL kullanmalıdır. Doğrudan API komutları modelin döndürdüğü araç çağrılarını kendiliğinden çalıştırmaz; otonom araç döngüsü `evren-agent` içindedir.

- `--metadata`: istek kimliği, `X-Evren-*`, hız/kota ve `Retry-After` başlıklarını stderr'e yazar.
- `--output DOSYA`: başarılı yanıtı atomik olarak yazar; hata olursa eski dosyayı korur.
- `--timeout SANİYE`: varsayılan 180; POST işlemleri otomatik tekrar edilmez.
- `--config DOSYA`: `providers.evren` içindeki adres, model ve `api_key_env` ayarlarını okur.
- `--base-url URL`: doğrudan API adresini değiştirir. `EVREN_BASE_URL` de desteklenir. Öncelik CLI → ortam → config → varsayılan.
- Çıkış kodları: başarı `0`, istek/girdi hatası `1`, argüman hatası `2`, Ctrl-C `130`.

HTTP 401/402/403/429/503 hataları sunucunun açıklamasıyla gösterilir. İstek kimliği ve hata içindeki `evren` alanları korunur. Kullanım/kota hatalarında `evren quota`, şart hatalarında `evren terms status` kullanın. CLI yeni anahtar üretmez veya şart kabulünü sessizce değiştirmez.

## Python istemcisi

```python
import asyncio
import os
from evren_agent.api import EvrenAPI

async def main():
    async with EvrenAPI(os.environ["EVREN_API_KEY"]) as api:
        print(await api.models())
        print(await api.quota())
        result = await api.embeddings("qwen3-embedding-8b", ["Merhaba", "Dünya"])
        print(result)
        async for event in api.stream("/v1/responses", {
            "model": "glm-5.3", "input": "Merhaba"
        }):
            print(event)

asyncio.run(main())
```

İstemci `chat`, `completions`, `responses`, `embeddings`, `rerank`, `ocr`, `transcribe`, `upload_media`, medya yaşam döngüsü, şartlar ve durum sorguları için metotlar sunar. Akış için `stream` kullanın; nesneyi `async with` ile veya `await api.close()` çağrısıyla kapatın.

## Agent ve MCP modu

Claude Code ve Codex CLI benzeri MCP sunucusu ekleme, listeleme ve kaldırma:

```bash
# MCP sunucusu ekleme ve config.yaml'a otomatik kaydetme:
evren-agent mcp add git npx -y @modelcontextprotocol/server-git
evren-agent mcp add sqlite uvx mcp-server-sqlite --db-path ./app.db
evren-agent mcp add github -e GITHUB_PERSONAL_ACCESS_TOKEN=ghp_xxx npx -y @modelcontextprotocol/server-github
evren-agent mcp add remote --url http://localhost:8000/sse

# Sunucuları listeleme ve kaldırma:
evren-agent mcp list
evren-agent mcp list --test
evren-agent mcp remove git    # veya: evren-agent mcp rm git

# (Aynı komutlar 'evren mcp add ...' olarak da çalışır)
```

İnteraktif agent ve testler:

```bash
evren-agent
evren-agent -p 'Bu soruyu araçlarla çöz'
evren-agent --provider llmtr --model evren/glm-5.3-fp8
pytest -q
```

[Detaylı MCP, skill, plugin ve agent kullanım kılavuzu](docs/AGENT.md). Agent REPL'inde `/api ...` için doğrudan `evren` sağlayıcısını seçin. Birim/kontrat testleri sahte HTTP transport kullanır; gerçek anahtara veya ücretli API çağrılarına ihtiyaç duymaz.

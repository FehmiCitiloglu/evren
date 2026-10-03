# Git God

Projeyi açıp **Git God** sekmesine geçin. Kodlama Ajanı → **Git** aynı görünümü sohbetin yanında açar; üstteki açma düğmesi geniş çalışma alanına geçer. Seçili klasör Git deposu değilse panel bunu bildirir. Git, sistemin PATH değişkeninde bulunmalıdır.

## Depoyu anlamak

- **Genel bakış:** Seçili zaman aralığındaki commit sayısı, katkıcılar, eklenen/silinen satırlar; katkıcı sıralaması, günlük aktivite haritası ve en çok değişen dosyalar. Rapor JSON ve CSV olarak dışa aktarılabilir.
- **Geçmiş:** Commit mesajı, yazar, tarih, dosya ve içerik değişikliği üzerinden arama. Commit seçildiğinde patch ve dosya değişiklikleri görüntülenir. Dal grafiği commitlerin ebeveyn ilişkilerini gösterir.
- **Satır sahipliği:** Dosyayı ve satır aralığını seçerek her satırın son yazarını, tarihini ve commitini inceleyin. Kaydedilmemiş satırlar ayrı belirtilir. Dosya geçmişi yeniden adlandırmaları takip eder.
- **Dallar:** Yerel ve uzak dal bilgileri, upstream ve ahead/behind; iki ref arasında ortak ata, commit ve dosya farkları.
- **Değişiklikler:** Çalışma ağacı ve stage alanındaki değişiklikleri inceleyin, seçili dosyayı stage alanına alın veya çıkarın, hazırlanmış değişiklikleri mesajla commit edin. Çatışmalar ayrıca gösterilir.
- **Araç kutusu:** 72 aracın yer aldığı aranabilir katalog, amaca yönelik açıklamalar, parametre alanları, komut önizlemesi ve gerçek çıktı.
- **Kurtarma:** Reflog, stash, worktree ve etiketler. Reflogdan bulunan commit için kurtarma dalı oluşturma aracı kullanılabilir.

**Ajana sor** düğmeleri ilgili soruyu Kodlama Ajanı girişine yerleştirir. Soruyu düzenleyip **Gönder** ile gönderin. Dosya düğmeleri kayıtlı editör tercihini kullanır.

## İleri araçlardan örnekler

| İhtiyaç | Git aracı |
| --- | --- |
| Bir metni hangi commit ekledi/sildi? | `log -S` (pickaxe) |
| Değişen satırlarda belirli desen ne zaman göründü? | `log -G` |
| Belirli satırlar zaman içinde nasıl değişti? | `log -L` |
| Kod taşındığında satır yazarı kim? | `blame -M -C` |
| İki commit serisindeki değişiklikleri karşılaştır | `range-diff` |
| Birleştirme sonucunu önceden incele | `merge-tree` |
| Birleştirme veya rebase işlemini yönet | `merge`, `rebase`, devam/iptal araçları |
| Bir daldaki yamalar diğerinde zaten var mı? | `cherry` |
| Dosya neden Git tarafından yok sayılıyor? | `check-ignore -v` |
| Hata ilk hangi committe başladı? | Etkileşimli `bisect` |
| Kaybolan commit nerede? | `reflog`, kurtarma dalı |
| Başka dalı ayrı klasörde çalıştır | `worktree` |
| Depoyu taşınabilir yedekle | `bundle` |
| Yayına hazır kaynak arşivi çıkar | `archive` |
| Çatışmanın üç sürümünü incele | `ls-files --unmerged` |
| Fazladan dosyaları silmeden gör | `clean --dry-run` |
| Nesne bütünlüğünü incele | `fsck`, `count-objects` |

Araç önce çalışacak komutu gösterir. Depoyu veya dosyaları değiştiren işlemler aynı komutla uygulama içi onay ister. Commit yalnızca stage alanını kullanır; pull fast-forward ile çalışır. Merge/rebase/cherry-pick/revert çatışmasında hata, ilgili dosyalar ve devam/iptal araçları gösterilir. Bir hata sonrasında otomatik reset veya zorlamalı push yapılmaz. Bisect sırasında sürümleri test edip iyi/kötü olarak işaretleyin; bitince reset aracıyla başlangıç dalına dönün.

## Raporların anlamı

Katkı sayıları iş kalitesi, çalışma süresi veya performans puanı değildir. Commit yazarı, committer ve mevcut satırların son yazarı farklı kavramlardır. Dosyanın son değişikliğini dosya geçmişinden; mevcut satırın son değişikliğini blame üzerinden okuyun.

Rapor seçilen ref ve tarih aralığına aittir. Büyük depolarda örneklem sınırı ve kesilmiş çıktılar görünümde belirtilir. Shallow clone yalnızca indirilen geçmişi içerir. İkili dosyalar için Git satır sayısı sağlamaz. Raporun kapsam açıklaması merge commitlerinin nasıl sayıldığını belirtir. Uzak dal bilgileri son fetch zamanındaki yerel verilerdir; panel kendiliğinden ağa bağlanmaz. Henüz commit olmayan bir depoda grafikler boş olabilir.

Aktivite haritası committer tarihlerini UTC günlerine göre gruplar ve en fazla 365 günü gösterir. Katkıcı sıralaması commit yazarını kullanır; Git mailmap eşleştirmeleri uygulanır. Dal grafiği en yeni 10 commitin ebeveyn ilişkilerini gösterir; geçmiş tablosunda daha fazla kayıt incelenebilir. Merge commitleri commit sayısına dahil edilir; satır değişimi toplamlarında merge dışındaki commitler kullanılır. Bu kapsam bilgileri panelde de gösterilir.

Git sorguları GUI ve ajan döngüsünün dışında çalışır. Dosya adları NUL ayraçlarıyla okunur; boşluklar, Türkçe karakterler ve yeniden adlandırmalar korunur. Çalıştırma shell kullanmaz; komut argümanları ayrı verilir. Git çıktı ve süre sınırları aşıldığında sorguyu daraltmanızı isteyen hata gösterilir.

## Kodlama ajanı araçları

- `git_inspect`: Durum, katkı raporu, commit geçmişi, dosya geçmişi, blame, dallar, ref karşılaştırması, commit ayrıntısı, kurtarma kayıtları. `cwd` verilmezse aktif projenin klasörü kullanılır.
- `git_tools`: Parametresiz çağrı katalog döndürür; `tool_id` ve `params` ile okuma araçlarını çalıştırır. Değişiklik yapan araçlar uygulama içi onay için önizleme döndürür.
- `git_prepare`: İşlem etkilerini, tam argümanları ve uyarıları gösterir; çalıştırmaz.

Bu özellik kaynak koddan çalıştırılan uygulamada doğrudan kullanılabilir. Daha önce kurulmuş bir paket, yeni kaynak dosyalarıyla kendiliğinden güncellenmez; paket yeniden oluşturulmalı veya yeni sürüm kurulmalıdır.

Git semantiği için: [status](https://git-scm.com/docs/git-status), [blame](https://git-scm.com/docs/git-blame), [log](https://git-scm.com/docs/git-log).

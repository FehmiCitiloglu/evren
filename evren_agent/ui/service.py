"""evren masaüstü uygulaması arka plan API servis köprüsü.

Tüm ağ isteklerini arka plan iş parçacıklarında (threads) çalıştırarak
grafik arayüzün (GUI) donmasını engeller ve tüm hata mesajlarını
anlaşılır Türkçe metinlere dönüştürür.
"""
from __future__ import annotations

import asyncio
import json
import os
import threading
import sys
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

import httpx

from evren_agent.api.client import DEFAULT_BASE_URL, EvrenAPI, EvrenAPIError, media_data_url
from evren_agent.config import load_config, save_config
from evren_agent.credentials import get_api_key, set_api_key
from evren_agent.projects.service import ProjectService



# Çevrimdışı veya ilk yüklemede gösterilecek popüler varsayılan modeller
VARSAYILAN_MODELLER = [
    "glm-5.3",
    "qwen-2.5-72b-instruct",
    "deepseek-r1",
    "dots-ocr",
    "qwen3-asr-1.7b",
    "bge-reranker-large",
]


def turkce_hata_mesaji(hata: Exception) -> str:
    """Teknik istisnaları kullanıcı dostu Türkçe hata mesajlarına çevirir."""
    if isinstance(hata, EvrenAPIError):
        durum = getattr(hata, "status_code", 0)
        govde = getattr(hata, "body", "")
        detay = ""
        if isinstance(govde, dict):
            detay = govde.get("detail") or govde.get("message") or json.dumps(govde, ensure_ascii=False)
        elif govde:
            detay = str(govde)

        if durum == 401:
            return "Kimlik doğrulama başarısız (401): API anahtarınız geçersiz veya eksik. Lütfen Ayarlar sekmesinden geçerli bir LLM Çıkarım anahtarı girin."
        elif durum == 402:
            return f"Yetersiz Kredi (402): Hesabınızdaki kredi tükenmiş. {detay}"
        elif durum == 403:
            return f"Erişim Engellendi (403): Anahtar yetkisi yetersiz veya Kullanım Şartları kabul edilmemiş. Lütfen 'Kota ve Durum' sekmesinden şartları onaylayın. {detay}"
        elif durum == 429:
            return f"Hız/Kota Sınırı Aşıldı (429): Lütfen bir süre bekleyip tekrar deneyin. {detay}"
        elif durum == 503:
            return "Sunucu Hizmet Veremiyor (503): EVREN sunucuları şu anda meşgul veya bakımda."
        return f"EVREN API Hatası ({durum}): {detay or str(hata)}"

    if isinstance(hata, httpx.ConnectError):
        return "Sunucuya bağlanılamadı. Lütfen internet bağlantınızı veya API adresini (URL) kontrol edin."
    if isinstance(hata, httpx.TimeoutException):
        return "İstek zaman aşımına uğradı. Sunucu yanıt vermedi, lütfen zaman aşımı süresini artırın veya tekrar deneyin."
    if isinstance(hata, ValueError):
        return str(hata)
    return f"Beklenmeyen bir hata oluştu: {str(hata)}"


class EvrenService:
    """evren masaüstü uygulaması için merkezi API yöneticisi."""

    def __init__(self, dispatch=None) -> None:
        self._dispatch = dispatch or (lambda callback, *args: callback(*args))
        self.config_path = None
        if getattr(sys, "frozen", False):
            if sys.platform == "win32":
                base = Path(os.environ.get("APPDATA", Path.home() / "AppData/Roaming"))
            elif sys.platform == "darwin":
                base = Path.home() / "Library/Application Support"
            else:
                base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
            self.config_path = base / "evren" / "config.yaml"
        self.config = load_config(self.config_path)
        self.provider = "evren"
        self._provider_cfg = self.config.get("providers", {}).get(self.provider, {})
        self.base_url = self._provider_cfg.get("base_url", DEFAULT_BASE_URL)
        self.default_model = self._provider_cfg.get("default_model", "glm-5.3")
        self.timeout = float(self.config.get("timeout", 180.0))
        self._cached_models: List[str] = VARSAYILAN_MODELLER.copy()
        self._active_stream_cancel: Optional[threading.Event] = None
        db_path = None
        if self.config_path:
            db_path = self.config_path.parent / "projects.db"
        self.projects = ProjectService(db_path=db_path)


    def get_key(self) -> str:
        """Kayıtlı API anahtarını işletim sistemi kasasından veya ortamdan okur."""
        return get_api_key(self.provider, self._provider_cfg, base_url=self.base_url)

    def set_key(self, key: str) -> None:
        """API anahtarını güvenli kasaya (Keyring) kaydeder."""
        set_api_key(self.provider, self._provider_cfg, key, base_url=self.base_url)

    def update_settings(self, base_url: str, default_model: str, timeout: float) -> None:
        """Ayarları günceller ve config.yaml dosyasına kaydeder."""
        self.base_url = base_url.strip()
        self.default_model = default_model.strip()
        self.timeout = float(timeout)

        if "providers" not in self.config:
            self.config["providers"] = {}
        if self.provider not in self.config["providers"]:
            self.config["providers"][self.provider] = {}

        self.config["providers"][self.provider]["base_url"] = self.base_url
        self.config["providers"][self.provider]["default_model"] = self.default_model
        self.config["timeout"] = self.timeout
        if self.config_path is not None:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
        save_config(self.config, self.config_path)

    def test_connection_async(
        self,
        on_success: Callable[[Dict[str, Any]], None],
        on_error: Callable[[str], None],
    ) -> None:
        """Sunucu sağlık ve hazırlık kontrolünü arka planda yürütür."""
        def worker():
            async def run():
                async with EvrenAPI(self.get_key(), self.base_url, timeout=self.timeout) as client:
                    health = await client.request("GET", "/healthz")
                    ready = await client.request("GET", "/readyz")
                    return {"health": health, "ready": ready}

            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(run())
                loop.close()
                self._dispatch(on_success, result)
            except Exception as e:
                self._dispatch(on_error, turkce_hata_mesaji(e))

        threading.Thread(target=worker, daemon=True).start()

    def fetch_models_async(
        self,
        on_success: Callable[[List[str]], None],
        on_error: Optional[Callable[[str], None]] = None,
    ) -> None:
        """Model listesini arka planda çeker."""
        def worker():
            async def run():
                async with EvrenAPI(self.get_key(), self.base_url, timeout=self.timeout) as client:
                    data = await client.models()
                    models = []
                    if isinstance(data, dict) and "data" in data:
                        models = [item.get("id") for item in data["data"] if item.get("id")]
                    elif isinstance(data, list):
                        models = [item.get("id") if isinstance(item, dict) else str(item) for item in data]
                    return models or VARSAYILAN_MODELLER

            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                models = loop.run_until_complete(run())
                loop.close()
                self._cached_models = models
                self._dispatch(on_success, models)
            except Exception as e:
                # Ağ hatasında önbellekteki modelleri döner
                self._dispatch(on_success, self._cached_models)
                if on_error:
                    self._dispatch(on_error, turkce_hata_mesaji(e))

        threading.Thread(target=worker, daemon=True).start()

    def fetch_quota_async(
        self,
        on_success: Callable[[Dict[str, Any]], None],
        on_error: Callable[[str], None],
    ) -> None:
        """Kota, bakiye ve şart durumunu arka planda sorgular."""
        def worker():
            async def run():
                key = self.get_key()
                if not key:
                    raise ValueError("API anahtarı bulunamadı. Lütfen Ayarlar sekmesinden anahtarınızı girin.")
                async with EvrenAPI(key, self.base_url, timeout=self.timeout) as client:
                    quota = await client.quota()
                    terms = await client.terms_status()
                    return {"quota": quota, "terms": terms}

            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                data = loop.run_until_complete(run())
                loop.close()
                self._dispatch(on_success, data)
            except Exception as e:
                self._dispatch(on_error, turkce_hata_mesaji(e))

        threading.Thread(target=worker, daemon=True).start()

    def fetch_terms_text_async(
        self,
        on_success: Callable[[str], None],
        on_error: Callable[[str], None],
    ) -> None:
        """Kullanım şartları metnini çeker."""
        def worker():
            async def run():
                async with EvrenAPI(self.get_key(), self.base_url, timeout=self.timeout) as client:
                    res = await client.terms_text()
                    if isinstance(res, dict):
                        return res.get("text", json.dumps(res, ensure_ascii=False, indent=2))
                    return str(res)

            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                text = loop.run_until_complete(run())
                loop.close()
                self._dispatch(on_success, text)
            except Exception as e:
                self._dispatch(on_error, turkce_hata_mesaji(e))

        threading.Thread(target=worker, daemon=True).start()

    def accept_terms_async(
        self,
        version: int,
        on_success: Callable[[Any], None],
        on_error: Callable[[str], None],
    ) -> None:
        """Kullanım şartlarını onaylar."""
        def worker():
            async def run():
                async with EvrenAPI(self.get_key(), self.base_url, timeout=self.timeout) as client:
                    return await client.accept_terms(version)

            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                res = loop.run_until_complete(run())
                loop.close()
                self._dispatch(on_success, res)
            except Exception as e:
                self._dispatch(on_error, turkce_hata_mesaji(e))

        threading.Thread(target=worker, daemon=True).start()

    def cancel_active_stream(self) -> None:
        """Akış halindeki sohbet üretimini durdurur."""
        if self._active_stream_cancel:
            self._active_stream_cancel.set()

    def chat_stream_async(
        self,
        model: str,
        messages: List[Dict[str, Any]],
        temperature: float,
        max_tokens: int,
        evren_tools: bool,
        on_delta: Callable[[str], None],
        on_done: Callable[[str], None],
        on_error: Callable[[str], None],
    ) -> None:
        """Sohbet yanıtını SSE akışı olarak arka planda üretir."""
        cancel_event = threading.Event()
        self._active_stream_cancel = cancel_event

        def worker():
            accumulated: List[str] = []

            async def run():
                key = self.get_key()
                if not key:
                    raise ValueError("API anahtarı bulunamadı. Lütfen Ayarlar sekmesinden anahtarınızı girin.")

                body: Dict[str, Any] = {
                    "model": model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }
                if evren_tools:
                    body["evren_tools"] = True

                async with EvrenAPI(key, self.base_url, timeout=self.timeout) as client:
                    async for event in client.stream("/v1/chat/completions", body):
                        if cancel_event.is_set():
                            break
                        data = event.get("data")
                        if not isinstance(data, dict):
                            continue
                        # Delta çıkarımı
                        delta_text = ""
                        for choice in data.get("choices", []):
                            delta_text += choice.get("delta", {}).get("content") or ""
                        if delta_text:
                            accumulated.append(delta_text)
                            self._dispatch(on_delta, delta_text)

            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(run())
                loop.close()
                full_text = "".join(accumulated)
                self._dispatch(on_done, full_text)
            except Exception as e:
                if cancel_event.is_set():
                    self._dispatch(on_done, "".join(accumulated))
                else:
                    self._dispatch(on_error, turkce_hata_mesaji(e))
            finally:
                if self._active_stream_cancel is cancel_event:
                    self._active_stream_cancel = None

        threading.Thread(target=worker, daemon=True).start()

    def ocr_async(
        self,
        model: str,
        image_path: str,
        on_success: Callable[[str], None],
        on_error: Callable[[str], None],
    ) -> None:
        """Görselden metin çıkarma (OCR) işlemini arka planda yürütür."""
        def worker():
            async def run():
                key = self.get_key()
                if not key:
                    raise ValueError("API anahtarı bulunamadı. Lütfen Ayarlar sekmesinden anahtarınızı girin.")
                data_url = media_data_url(image_path)
                async with EvrenAPI(key, self.base_url, timeout=self.timeout) as client:
                    res = await client.ocr(model=model, image=data_url)
                    if isinstance(res, dict):
                        return res.get("text") or res.get("content") or json.dumps(res, ensure_ascii=False, indent=2)
                    return str(res)

            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(run())
                loop.close()
                self._dispatch(on_success, result)
            except Exception as e:
                self._dispatch(on_error, turkce_hata_mesaji(e))

        threading.Thread(target=worker, daemon=True).start()

    def transcribe_async(
        self,
        audio_path: str,
        model: str,
        language: Optional[str],
        response_format: str,
        prompt: str,
        on_success: Callable[[str], None],
        on_error: Callable[[str], None],
    ) -> None:
        """Ses dosyasını çözümleme (Transkripsiyon) işlemini yürütür."""
        def worker():
            async def run():
                key = self.get_key()
                if not key:
                    raise ValueError("API anahtarı bulunamadı. Lütfen Ayarlar sekmesinden anahtarınızı girin.")

                opts: Dict[str, Any] = {"response_format": response_format}
                if language and language != "auto":
                    opts["language"] = language
                if prompt.strip():
                    opts["prompt"] = prompt.strip()

                async with EvrenAPI(key, self.base_url, timeout=self.timeout) as client:
                    res = await client.transcribe(filename=audio_path, model=model, **opts)
                    if isinstance(res, str):
                        return res
                    if isinstance(res, dict):
                        return res.get("text") or json.dumps(res, ensure_ascii=False, indent=2)
                    return str(res)

            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                result = loop.run_until_complete(run())
                loop.close()
                self._dispatch(on_success, result)
            except Exception as e:
                self._dispatch(on_error, turkce_hata_mesaji(e))

        threading.Thread(target=worker, daemon=True).start()

    def rerank_async(
        self,
        model: str,
        query: str,
        documents: List[str],
        on_success: Callable[[List[Dict[str, Any]]], None],
        on_error: Callable[[str], None],
    ) -> None:
        """Dokümanları arama sorgusuna göre yeniden sıralar."""
        def worker():
            async def run():
                key = self.get_key()
                if not key:
                    raise ValueError("API anahtarı bulunamadı. Lütfen Ayarlar sekmesinden anahtarınızı girin.")

                async with EvrenAPI(key, self.base_url, timeout=self.timeout) as client:
                    res = await client.rerank(model=model, query=query, documents=documents)
                    results: List[Dict[str, Any]] = []
                    if isinstance(res, dict) and "results" in res:
                        for item in res["results"]:
                            idx = item.get("index", 0)
                            doc_text = documents[idx] if idx < len(documents) else ""
                            results.append({
                                "index": idx,
                                "score": item.get("relevance_score", 0.0),
                                "text": doc_text,
                            })
                    return results

            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                items = loop.run_until_complete(run())
                loop.close()
                self._dispatch(on_success, items)
            except Exception as e:
                self._dispatch(on_error, turkce_hata_mesaji(e))

        threading.Thread(target=worker, daemon=True).start()

"""evren masaüstü uygulaması - Sohbet Görünümü (Chat View).

Akışlı (streaming) yanıt üretimi, çok modlu görsel desteği (multimodal),
parametre kontrolleri ve sohbet geçmişi yönetimi sunar.
Tüm etiket ve açıklamalar Türkçedir.
"""
from __future__ import annotations

import datetime
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional
import tkinter as tk
from tkinter import filedialog, messagebox

import customtkinter as ctk
from PIL import Image

from evren_agent.ui.service import EvrenService
from evren_agent.ui.theme import THEME_COLORS


class ChatMessageBubble(ctk.CTkFrame):
    """Sohbet mesaj balonu bileşeni."""

    def __init__(
        self,
        master: Any,
        role: str,
        content: str,
        image_path: Optional[str] = None,
        timestamp: Optional[str] = None,
        **kwargs: Any,
    ) -> None:
        is_user = (role == "user")
        theme_mode = ctk.get_appearance_mode().lower()
        colors = THEME_COLORS.get(theme_mode, THEME_COLORS["dark"])

        bg_color = colors["user_bubble"] if is_user else colors["bot_bubble"]
        fg_color = bg_color

        super().__init__(
            master,
            fg_color=fg_color,
            corner_radius=12,
            border_width=1,
            border_color=colors["border"],
            **kwargs,
        )

        self.role = role
        self.raw_content = content
        self.timestamp = timestamp or datetime.datetime.now().strftime("%H:%M")

        # Üst Bilgi Satırı (Gönderen ve Zaman Damgası)
        header_frame = ctk.CTkFrame(self, fg_color="transparent")
        header_frame.pack(fill="x", padx=12, pady=(8, 4))

        sender_title = "Siz" if is_user else "evren"
        sender_color = "#93c5fd" if is_user else "#38bdf8"
        sender_label = ctk.CTkLabel(
            header_frame,
            text=sender_title,
            font=ctk.CTkFont(size=13, weight="bold"),
            text_color=sender_color,
        )
        sender_label.pack(side="left")

        time_label = ctk.CTkLabel(
            header_frame,
            text=self.timestamp,
            font=ctk.CTkFont(size=11),
            text_color=colors["text_muted"],
        )
        time_label.pack(side="left", padx=8)

        # Kopyala butonu
        copy_btn = ctk.CTkButton(
            header_frame,
            text="Kopyala",
            width=58,
            height=22,
            font=ctk.CTkFont(size=11),
            fg_color="transparent",
            hover_color=colors["bg_hover"],
            text_color=colors["text_secondary"],
            command=self._copy_to_clipboard,
        )
        copy_btn.pack(side="right")

        # Varsa Görsel Önizlemesi
        if image_path and os.path.exists(image_path):
            try:
                pil_img = Image.open(image_path)
                pil_img.thumbnail((240, 180))
                ctk_thumb = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=pil_img.size)
                img_lbl = ctk.CTkLabel(self, image=ctk_thumb, text="")
                img_lbl.pack(anchor="w", padx=12, pady=4)
            except Exception:
                img_name = Path(image_path).name
                err_lbl = ctk.CTkLabel(self, text=f"📷 [Ekli Görsel: {img_name}]", font=ctk.CTkFont(size=11))
                err_lbl.pack(anchor="w", padx=12, pady=4)

        # Mesaj Metni
        self.text_label = ctk.CTkLabel(
            self,
            text=content,
            font=ctk.CTkFont(size=13),
            text_color=colors["text_primary"],
            wraplength=700,
            justify="left",
            anchor="w",
        )
        self.text_label.pack(fill="x", padx=12, pady=(2, 10))

    def update_text(self, new_text: str) -> None:
        """Akış sırasında metni dinamik günceller."""
        self.raw_content = new_text
        self.text_label.configure(text=new_text)

    def _copy_to_clipboard(self) -> None:
        self.clipboard_clear()
        self.clipboard_append(self.raw_content)


class ChatView(ctk.CTkFrame):
    """Sohbet Arayüzü Ana Görünümü."""

    def __init__(self, master: Any, service: EvrenService, **kwargs: Any) -> None:
        super().__init__(master, fg_color="transparent", **kwargs)
        self.service = service
        self.messages: List[Dict[str, Any]] = []
        self.attached_image_path: Optional[str] = None
        self.current_bot_bubble: Optional[ChatMessageBubble] = None
        self.is_streaming = False

        self._build_ui()
        self._load_models()

    def _build_ui(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)  # Mesaj alanı esner

        # 1. ÜST PANEL: Model Seçimi, Parametreler ve Aksiyon Butonları
        top_bar = ctk.CTkFrame(self, fg_color=("gray90", "#1e293b"), corner_radius=10)
        top_bar.grid(row=0, column=0, sticky="ew", padx=16, pady=(12, 6))

        # Model Seçici
        model_lbl = ctk.CTkLabel(top_bar, text="Model:", font=ctk.CTkFont(size=12, weight="bold"))
        model_lbl.pack(side="left", padx=(12, 4), pady=10)

        self.model_combo = ctk.CTkComboBox(
            top_bar,
            values=[self.service.default_model],
            width=180,
            command=self._on_model_selected,
        )
        self.model_combo.set(self.service.default_model)
        self.model_combo.pack(side="left", padx=4, pady=10)

        # Ayarları Göster / Gizle Butonu
        self.toggle_params_btn = ctk.CTkButton(
            top_bar,
            text="Parametreler ▼",
            width=110,
            height=28,
            fg_color="transparent",
            border_width=1,
            text_color=("gray20", "gray80"),
            command=self._toggle_params,
        )
        self.toggle_params_btn.pack(side="left", padx=8, pady=10)

        # Sağ Taraf Butonları: Yeni Sohbet & Dışa Aktar & Temizle
        clear_btn = ctk.CTkButton(
            top_bar,
            text="Temizle",
            width=70,
            height=28,
            fg_color="transparent",
            text_color=("gray30", "#94a3b8"),
            hover_color=("gray80", "#334155"),
            command=self.clear_chat,
        )
        clear_btn.pack(side="right", padx=(4, 12), pady=10)

        export_btn = ctk.CTkButton(
            top_bar,
            text="Dışa Aktar",
            width=85,
            height=28,
            fg_color="transparent",
            border_width=1,
            text_color=("gray20", "gray80"),
            command=self._export_chat,
        )
        export_btn.pack(side="right", padx=4, pady=10)

        new_chat_btn = ctk.CTkButton(
            top_bar,
            text="+ Yeni Sohbet",
            width=100,
            height=28,
            fg_color="#3b82f6",
            hover_color="#2563eb",
            command=self.new_chat,
        )
        new_chat_btn.pack(side="right", padx=4, pady=10)

        # 2. KATLANABİLİR PARAMETRE PANELİ
        self.params_frame = ctk.CTkFrame(self, fg_color=("gray95", "#161f2e"), corner_radius=8)
        self.params_visible = False

        # Sıcaklık (Temperature)
        t_frame = ctk.CTkFrame(self.params_frame, fg_color="transparent")
        t_frame.pack(side="left", padx=12, pady=8)
        self.temp_label = ctk.CTkLabel(t_frame, text="Sıcaklık: 0.7", font=ctk.CTkFont(size=11))
        self.temp_label.pack(anchor="w")
        self.temp_slider = ctk.CTkSlider(
            t_frame,
            from_=0.0,
            to=1.5,
            number_of_steps=15,
            width=130,
            command=self._on_temp_change,
        )
        self.temp_slider.set(0.7)
        self.temp_slider.pack(anchor="w", pady=(2, 0))

        # Maksimum Belirteç (Max Tokens)
        tok_frame = ctk.CTkFrame(self.params_frame, fg_color="transparent")
        tok_frame.pack(side="left", padx=12, pady=8)
        self.tokens_label = ctk.CTkLabel(tok_frame, text="Maks. Belirteç: 2048", font=ctk.CTkFont(size=11))
        self.tokens_label.pack(anchor="w")
        self.tokens_slider = ctk.CTkSlider(
            tok_frame,
            from_=256,
            to=8192,
            number_of_steps=31,
            width=140,
            command=self._on_tokens_change,
        )
        self.tokens_slider.set(2048)
        self.tokens_slider.pack(anchor="w", pady=(2, 0))

        # Canlı Araçlar (Evren Tools)
        self.tools_var = tk.BooleanVar(value=False)
        self.tools_check = ctk.CTkCheckBox(
            self.params_frame,
            text="Canlı Web/Veri Araçları",
            variable=self.tools_var,
            font=ctk.CTkFont(size=12),
        )
        self.tools_check.pack(side="left", padx=14, pady=8)

        # Sistem Yönergesi (System Prompt) Girişi
        sys_frame = ctk.CTkFrame(self.params_frame, fg_color="transparent")
        sys_frame.pack(side="left", fill="x", expand=True, padx=12, pady=8)
        sys_lbl = ctk.CTkLabel(sys_frame, text="Sistem Talimatı:", font=ctk.CTkFont(size=11))
        sys_lbl.pack(anchor="w")
        self.sys_entry = ctk.CTkEntry(
            sys_frame,
            placeholder_text="Asistanın kimliği ve davranış yönergeleri...",
            height=28,
            font=ctk.CTkFont(size=11),
        )
        self.sys_entry.pack(fill="x", pady=(2, 0))

        # 3. SOHBET AKIŞ ALANI (Scrollable)
        self.chat_scroll = ctk.CTkScrollableFrame(
            self,
            fg_color="transparent",
            corner_radius=0,
        )
        self.chat_scroll.grid(row=1, column=0, sticky="nsew", padx=16, pady=4)
        self.chat_scroll.grid_columnconfigure(0, weight=1)

        # Hoş Geldiniz Mesaj Kartı
        self._add_welcome_card()

        # 4. EKLİ GÖRSEL ÇUBUĞU (Varsa gösterilir)
        self.img_tray = ctk.CTkFrame(self, fg_color=("gray85", "#243044"), corner_radius=8, height=36)
        self.img_tray_lbl = ctk.CTkLabel(
            self.img_tray,
            text="",
            font=ctk.CTkFont(size=11),
            text_color="#38bdf8",
        )
        self.img_tray_lbl.pack(side="left", padx=10)
        self.img_remove_btn = ctk.CTkButton(
            self.img_tray,
            text="✕ Kaldır",
            width=65,
            height=22,
            fg_color="#ef4444",
            hover_color="#dc2626",
            font=ctk.CTkFont(size=11),
            command=self._remove_attached_image,
        )
        self.img_remove_btn.pack(side="right", padx=10)

        # 5. ALT GİRDİ PANELİ
        bottom_box = ctk.CTkFrame(self, fg_color=("gray90", "#1e293b"), corner_radius=12)
        bottom_box.grid(row=3, column=0, sticky="ew", padx=16, pady=(4, 12))
        bottom_box.grid_columnconfigure(1, weight=1)

        # Görsel Ekle Butonu
        self.add_img_btn = ctk.CTkButton(
            bottom_box,
            text="📷 Görsel",
            width=80,
            height=40,
            fg_color="transparent",
            border_width=1,
            text_color=("gray20", "gray85"),
            command=self._select_image,
        )
        self.add_img_btn.grid(row=0, column=0, padx=(10, 6), pady=10)

        # Çok Satırlı Metin Girdisi
        self.input_textbox = ctk.CTkTextbox(
            bottom_box,
            height=70,
            font=ctk.CTkFont(size=13),
            fg_color=("white", "#0f172a"),
            border_width=1,
            corner_radius=8,
        )
        self.input_textbox.grid(row=0, column=1, sticky="ew", padx=6, pady=10)
        self.input_textbox.bind("<Return>", self._handle_return_key)
        self.input_textbox.bind("<KP_Enter>", self._handle_return_key)

        # Gönder / Durdur Butonu
        self.send_btn = ctk.CTkButton(
            bottom_box,
            text="Gönder",
            width=90,
            height=40,
            font=ctk.CTkFont(size=13, weight="bold"),
            fg_color="#3b82f6",
            hover_color="#2563eb",
            command=self._on_send_pressed,
        )
        self.send_btn.grid(row=0, column=2, padx=(6, 10), pady=10)

        # Kısayol İpucu
        hint_lbl = ctk.CTkLabel(
            self,
            text="Göndermek için Enter veya Ctrl+Enter tuşlarına basın. Yeni satır için Shift+Enter kullanın.",
            font=ctk.CTkFont(size=10),
            text_color=("gray50", "gray60"),
        )
        hint_lbl.grid(row=4, column=0, sticky="w", padx=22, pady=(0, 6))

    def _add_welcome_card(self) -> None:
        """İlk açılış bilgilendirme kartı."""
        welcome = ctk.CTkFrame(
            self.chat_scroll,
            fg_color=("gray95", "#161f2e"),
            corner_radius=12,
            border_width=1,
            border_color=("gray85", "#334155"),
        )
        welcome.pack(fill="x", padx=16, pady=24)

        t_lbl = ctk.CTkLabel(
            welcome,
            text="evren Sohbet Ortamına Hoş Geldiniz",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color="#38bdf8",
        )
        t_lbl.pack(anchor="w", padx=16, pady=(14, 4))

        d_lbl = ctk.CTkLabel(
            welcome,
            text=(
                "EVREN LLM API üzerinden gelişmiş yapay zekâ modelleriyle hızlıca sohbet edin.\n"
                "• Metin soruları sorabilir, kod yazdırabilir ve belgeleri özetleyebilirsiniz.\n"
                "• '📷 Görsel' butonuyla fotoğraf veya ekran görüntüsü ekleyip görsel hakkında analiz isteyebilirsiniz.\n"
                "• 'Canlı Web/Veri Araçları' seçeneği ile güncel bilgilere erişebilirsiniz."
            ),
            font=ctk.CTkFont(size=12),
            text_color=("gray30", "#94a3b8"),
            justify="left",
        )
        d_lbl.pack(anchor="w", padx=16, pady=(0, 14))

    def _toggle_params(self) -> None:
        if self.params_visible:
            self.params_frame.grid_forget()
            self.toggle_params_btn.configure(text="Parametreler ▼")
            self.params_visible = False
        else:
            self.params_frame.grid(row=1, column=0, sticky="ew", padx=16, pady=(0, 6))
            self.chat_scroll.grid(row=2, column=0, sticky="nsew", padx=16, pady=4)
            self.toggle_params_btn.configure(text="Parametreler ▲")
            self.params_visible = True

    def _on_temp_change(self, value: float) -> None:
        self.temp_label.configure(text=f"Sıcaklık: {value:.1f}")

    def _on_tokens_change(self, value: float) -> None:
        self.tokens_label.configure(text=f"Maks. Belirteç: {int(value)}")

    def _load_models(self) -> None:
        """API'den modelleri listeler."""
        def on_models(models: List[str]):
            if models:
                self.model_combo.configure(values=models)
                if self.service.default_model in models:
                    self.model_combo.set(self.service.default_model)
                else:
                    self.model_combo.set(models[0])

        self.service.fetch_models_async(on_success=on_models)

    def _on_model_selected(self, model: str) -> None:
        pass

    def _select_image(self) -> None:
        """Multimodal sohbet için görsel dosyası seçer."""
        dosya = filedialog.askopenfilename(
            title="Görsel Seç",
            filetypes=[
                ("Görsel Dosyaları", "*.png *.jpg *.jpeg *.webp *.bmp *.gif"),
                ("Tüm Dosyalar", "*.*"),
            ],
        )
        if dosya:
            self.attached_image_path = dosya
            boyut_kb = os.path.getsize(dosya) / 1024
            self.img_tray_lbl.configure(text=f"📷 Eklenen Görsel: {Path(dosya).name} ({boyut_kb:.1f} KB)")
            self.img_tray.grid(row=2, column=0, sticky="ew", padx=16, pady=(0, 4))

    def _remove_attached_image(self) -> None:
        self.attached_image_path = None
        self.img_tray.grid_forget()

    def _handle_return_key(self, event: Any) -> str:
        # Shift+Enter yeni satır bırakır
        if event.state & 0x0001:  # Shift basılı
            return ""
        # Düz Enter veya Ctrl+Enter gönderir
        self._on_send_pressed()
        return "break"

    def _on_send_pressed(self) -> None:
        if self.is_streaming:
            # Durdur
            self.service.cancel_active_stream()
            self._finish_streaming()
            return

        text = self.input_textbox.get("1.0", "end-1c").strip()
        if not text and not self.attached_image_path:
            return

        model = self.model_combo.get().strip()
        if not model:
            messagebox.showwarning("Model Gerekli", "Lütfen bir model seçiniz.")
            return

        # Kullanıcı balonunu ekle
        user_bubble = ChatMessageBubble(
            self.chat_scroll,
            role="user",
            content=text,
            image_path=self.attached_image_path,
        )
        user_bubble.pack(fill="x", padx=12, pady=6)

        # Mesaj listesine ekle
        image_to_send = self.attached_image_path
        self._remove_attached_image()
        self.input_textbox.delete("1.0", "end")

        # Multimodal içerik hazırlığı
        if image_to_send:
            try:
                from evren_agent.api.client import media_data_url
                data_url = media_data_url(image_to_send)
                user_content = [
                    {"type": "text", "text": text or "Bu görseli inceleyip açıkla."},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ]
            except Exception as e:
                messagebox.showerror("Görsel Hatası", f"Görsel hazırlanamadı: {e}")
                return
        else:
            user_content = text

        self.messages.append({"role": "user", "content": user_content})

        # Asistan balonunu hazırla
        self.current_bot_bubble = ChatMessageBubble(
            self.chat_scroll,
            role="assistant",
            content="Yanıt hazırlanıyor...",
        )
        self.current_bot_bubble.pack(fill="x", padx=12, pady=6)

        self._scroll_to_bottom()

        # Akışı Başlat
        self.is_streaming = True
        self.send_btn.configure(text="Durdur", fg_color="#ef4444", hover_color="#dc2626")

        # Sistem yönergesi
        full_messages: List[Dict[str, Any]] = []
        sys_prompt = self.sys_entry.get().strip()
        if sys_prompt:
            full_messages.append({"role": "system", "content": sys_prompt})
        full_messages.extend(self.messages)

        accumulated_chunks: List[str] = []

        def on_delta(delta: str):
            accumulated_chunks.append(delta)
            if self.current_bot_bubble:
                self.current_bot_bubble.update_text("".join(accumulated_chunks))
                self._scroll_to_bottom()

        def on_done(full_text: str):
            if self.current_bot_bubble:
                self.current_bot_bubble.update_text(full_text or "".join(accumulated_chunks) or "(Yanıt boş)")
            self.messages.append({"role": "assistant", "content": full_text or "".join(accumulated_chunks)})
            self._finish_streaming()

        def on_error(err_msg: str):
            if self.current_bot_bubble:
                self.current_bot_bubble.update_text(f"⚠️ Hata: {err_msg}")
            self._finish_streaming()

        self.service.chat_stream_async(
            model=model,
            messages=full_messages,
            temperature=float(self.temp_slider.get()),
            max_tokens=int(self.tokens_slider.get()),
            evren_tools=self.tools_var.get(),
            on_delta=lambda d: self.after(0, lambda: on_delta(d)),
            on_done=lambda t: self.after(0, lambda: on_done(t)),
            on_error=lambda e: self.after(0, lambda: on_error(e)),
        )

    def _finish_streaming(self) -> None:
        self.is_streaming = False
        self.send_btn.configure(text="Gönder", fg_color="#3b82f6", hover_color="#2563eb")
        self._scroll_to_bottom()

    def _scroll_to_bottom(self) -> None:
        self.after(50, lambda: self.chat_scroll._parent_canvas.yview_moveto(1.0))

    def new_chat(self) -> None:
        """Yeni bir sohbet oturumu başlatır."""
        if self.messages:
            cevap = messagebox.askyesno("Yeni Sohbet", "Mevcut sohbet temizlenip yeni sohbet başlatılsın mı?")
            if not cevap:
                return
        self.clear_chat()

    def clear_chat(self) -> None:
        """Tüm sohbet geçmişini temizler."""
        self.messages.clear()
        self._remove_attached_image()
        for widget in self.chat_scroll.winfo_children():
            widget.destroy()
        self._add_welcome_card()

    def _export_chat(self) -> None:
        """Sohbeti Markdown veya JSON olarak dışa aktarır."""
        if not self.messages:
            messagebox.showinfo("Boş Sohbet", "Dışa aktarılacak mesaj bulunmuyor.")
            return

        dosya = filedialog.asksaveasfilename(
            title="Sohbeti Kaydet",
            defaultextension=".md",
            filetypes=[
                ("Markdown Dosyası", "*.md"),
                ("JSON Dosyası", "*.json"),
                ("Düz Metin", "*.txt"),
            ],
        )
        if not dosya:
            return

        try:
            if dosya.endswith(".json"):
                with open(dosya, "w", encoding="utf-8") as f:
                    json.dump(self.messages, f, ensure_ascii=False, indent=2)
            else:
                lines = [f"# evren Sohbet Dökümü - {datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n"]
                for msg in self.messages:
                    sender = "Siz" if msg["role"] == "user" else "evren"
                    content = msg["content"]
                    if isinstance(content, list):
                        # Multimodal parçalar
                        text_part = next((item["text"] for item in content if item.get("type") == "text"), "")
                        content = f"[Görsel Ekli]\n{text_part}"
                    lines.append(f"### {sender}\n{content}\n\n---\n")

                with open(dosya, "w", encoding="utf-8") as f:
                    f.writelines(lines)

            messagebox.showinfo("Başarılı", f"Sohbet başarıyla kaydedildi:\n{dosya}")
        except Exception as e:
            messagebox.showerror("Kayıt Hatası", f"Dosya kaydedilemedi: {e}")

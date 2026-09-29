from __future__ import annotations
import json
from typing import Any, Dict, Optional
import customtkinter as ctk

from evren_agent.mcp.models import redact_secrets
from evren_agent.ui.theme import THEME_COLORS


class ToolActivityBubble(ctk.CTkFrame):
    """
    Collapsible card component for displaying tool invocations in the chat view.
    Renders tool name, target MCP server, execution status, runtime duration,
    and an expandable drawer for arguments and output preview.
    """

    def __init__(
        self,
        master: Any,
        tool_name: str,
        server_name: Optional[str] = None,
        arguments: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> None:
        theme_mode = ctk.get_appearance_mode().lower()
        colors = THEME_COLORS.get(theme_mode, THEME_COLORS["dark"])

        super().__init__(
            master,
            fg_color=("gray92", "#131d2e"),
            corner_radius=10,
            border_width=1,
            border_color=("gray80", "#243247"),
            **kwargs,
        )

        self.tool_name = tool_name
        self.server_name = server_name or (tool_name.split("_")[1] if tool_name.startswith("mcp_") else "Sistem")
        self.arguments = arguments or {}
        self.output_content: str = ""
        self.error_content: str = ""
        self.duration_ms: Optional[float] = None
        self.is_expanded: bool = False
        self._colors = colors

        self._build_header()
        self._build_details()

    def _build_header(self) -> None:
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(fill="x", padx=10, pady=6)

        # Icon / Server label
        icon_text = "🔌" if self.server_name != "Sistem" else "⚙️"
        display_server = self.server_name.capitalize() if self.server_name else "Sistem"
        display_tool = self.tool_name
        if display_tool.startswith(f"mcp_{self.server_name}_"):
            display_tool = display_tool[len(f"mcp_{self.server_name}_"):]

        self.title_label = ctk.CTkLabel(
            self.header_frame,
            text=f"{icon_text}  {display_server} · {display_tool}",
            font=ctk.CTkFont(size=12, weight="bold"),
            text_color="#38bdf8",
        )
        self.title_label.pack(side="left")

        # Status badge
        self.status_badge = ctk.CTkLabel(
            self.header_frame,
            text="Çalışıyor...",
            font=ctk.CTkFont(size=11),
            text_color="#f59e0b",
        )
        self.status_badge.pack(side="left", padx=10)

        # Toggle Expand Button
        self.toggle_btn = ctk.CTkButton(
            self.header_frame,
            text="Detay ▼",
            width=65,
            height=22,
            font=ctk.CTkFont(size=10),
            fg_color="transparent",
            hover_color=("gray80", "#1e293b"),
            text_color=("gray30", "#94a3b8"),
            command=self._toggle_expand,
        )
        self.toggle_btn.pack(side="right")

    def _build_details(self) -> None:
        self.details_frame = ctk.CTkFrame(self, fg_color=("gray88", "#0b1320"), corner_radius=6)

        # Arguments preview
        args_str = json.dumps(self.arguments, indent=2, ensure_ascii=False) if self.arguments else "{}"
        clean_args = redact_secrets(args_str)
        self.args_label = ctk.CTkLabel(
            self.details_frame,
            text=f"Parametreler:\n{clean_args}",
            font=ctk.CTkFont(family="monospace", size=10),
            text_color=("gray30", "#cbd5e1"),
            justify="left",
            anchor="w",
            wraplength=640,
        )
        self.args_label.pack(fill="x", padx=8, pady=(6, 2))

        # Output preview
        self.output_label = ctk.CTkLabel(
            self.details_frame,
            text="Sonuç bekleniyor...",
            font=ctk.CTkFont(family="monospace", size=10),
            text_color=("gray40", "#94a3b8"),
            justify="left",
            anchor="w",
            wraplength=640,
        )
        self.output_label.pack(fill="x", padx=8, pady=(2, 6))

    def _toggle_expand(self) -> None:
        if self.is_expanded:
            self.details_frame.pack_forget()
            self.toggle_btn.configure(text="Detay ▼")
            self.is_expanded = False
        else:
            self.details_frame.pack(fill="x", padx=8, pady=(0, 6))
            self.toggle_btn.configure(text="Detay ▲")
            self.is_expanded = True

    def set_result(self, content: str, duration_ms: Optional[float] = None) -> None:
        self.output_content = content
        self.duration_ms = duration_ms
        dur_str = f" ({duration_ms:.0f}ms)" if duration_ms is not None else ""
        self.status_badge.configure(text=f"✓ Tamamlandı{dur_str}", text_color="#10b981")

        # Preview output truncated if very long
        preview = redact_secrets(content)
        if len(preview) > 500:
            preview = preview[:500] + f"\n... [{len(content) - 500} karakter daha]"
        self.output_label.configure(text=f"Çıktı:\n{preview}", text_color=("gray20", "#e2e8f0"))

    def set_error(self, error_msg: str, duration_ms: Optional[float] = None) -> None:
        self.error_content = error_msg
        self.duration_ms = duration_ms
        dur_str = f" ({duration_ms:.0f}ms)" if duration_ms is not None else ""
        self.status_badge.configure(text=f"✕ Hata{dur_str}", text_color="#ef4444")
        self.output_label.configure(text=f"Hata Dökümü:\n{redact_secrets(error_msg)}", text_color="#f87171")

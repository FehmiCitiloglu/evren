"""Desktop chat layout and event lifecycle regressions (requires a Tk display)."""
import time
import tempfile
import gc
from pathlib import Path

import customtkinter as ctk
import pytest

from evren_agent.core.events import AgentEvent, AgentEventType
from evren_agent.core.chat_history import ChatHistoryStore
from evren_agent.core.session import ChatSession
from evren_agent.ui.app import _ensure_tk_environment
from evren_agent.ui.views.chat_view import ChatMessageBubble, ChatView


@pytest.fixture(scope="module", autouse=True)
def collect_tk_objects_on_main_thread():
    # Tk fonts in widget/binding cycles must not be collected by a later API
    # worker. Collect them after all test roots have been destroyed instead.
    enabled = gc.isenabled()
    gc.disable()
    try:
        yield
    finally:
        gc.collect()
        if enabled:
            gc.enable()


class ChatServiceStub:
    default_model = "test-model"

    def __init__(self, history_path=None):
        self._directory = tempfile.TemporaryDirectory() if history_path is None else None
        self.chat_history = ChatHistoryStore(history_path or Path(self._directory.name) / "chats.db")
        self.session = ChatSession(model=self.default_model)
        self.sessions = {}
        self.streams = []
        self.cancelled = 0
        self.mcps = []

    def get_or_create_session(self, session_id=None):
        if session_id:
            return self.sessions.get(session_id) or self.restore_chat_session(session_id)
        self.session = ChatSession(model=self.default_model)
        self.sessions[self.session.session_id] = self.session
        return self.session

    def restore_chat_session(self, session_id):
        session = self.chat_history.restore_session(self.chat_history.load(session_id))
        self.sessions[session_id] = session
        return session

    def save_chat_transcript(self, session, messages):
        self.chat_history.save_transcript(session, messages)

    def list_chat_history(self):
        return self.chat_history.list_conversations()

    def load_chat_transcript(self, session_id):
        return self.chat_history.load(session_id)["transcript"]

    def delete_chat_history(self, session_id):
        self.chat_history.delete(session_id)
        self.sessions.pop(session_id, None)

    def add_mcp_listener(self, callback):
        pass

    def get_session_mcps(self, session_id):
        return self.mcps

    def fetch_models_async(self, on_success):
        on_success([self.default_model])

    def chat_agent_stream_async(self, **kwargs):
        self.streams.append(kwargs)

    def cancel_active_stream(self):
        self.cancelled += 1


def pump(root, seconds=0):
    end = time.monotonic() + seconds
    while True:
        root.update()
        if time.monotonic() >= end:
            break
        time.sleep(0.005)


@pytest.fixture
def chat():
    _ensure_tk_environment()
    ctk.set_appearance_mode("Dark")
    root = ctk.CTk()
    root.geometry("940x760")
    service = ChatServiceStub()
    view = ChatView(root, service)
    view.pack(fill="both", expand=True)
    pump(root)
    try:
        yield root, view, service
    finally:
        if view.winfo_exists():
            view.clear_chat()
        root.destroy()


def send(view, service, text="Bir sahne oluştur"):
    view.input_textbox.insert("1.0", text)
    view._on_send_pressed()
    return service.streams[-1]


def emit(root, stream, event_type, **kwargs):
    stream["on_event"](AgentEvent(event_type, stream["session_id"], **kwargs))
    pump(root)


def messages(view):
    return [child for row in view.chat_scroll.winfo_children()
            for child in row.winfo_children() if isinstance(child, ChatMessageBubble)]


def test_message_alignment_wrap_and_panels_do_not_overlap(chat, tmp_path, monkeypatch):
    root, view, service = chat
    service.mcps = ["blender-mcp"]
    view._update_mcp_chips()
    image = tmp_path / "image.png"
    from PIL import Image
    Image.new("RGB", (40, 40)).save(image)
    monkeypatch.setattr("tkinter.filedialog.askopenfilename", lambda **kwargs: str(image))
    send(view, service, "Uzun bir kullanıcı mesajı. " * 12)
    user, bot = messages(view)
    bot.update_text("Okunabilir bir model yanıtı. " * 40)
    view._select_image()

    for width in (660, 940, 1400):
        root.geometry(f"{width}x760")
        for _ in range(4):
            view._toggle_params()
            pump(root)
            assert view.chat_scroll.grid_info()["row"] == 3
            assert user.winfo_x() > bot.winfo_x()
            assert user.winfo_x() + user.winfo_width() == user.master.winfo_width()
            assert bot.winfo_x() == 0
            assert user.winfo_width() < user.master.winfo_width()
            assert bot.winfo_width() <= 800
            assert bot.text_label.cget("wraplength") <= bot.winfo_width() - 20
            canvas = view.chat_scroll._parent_canvas
            assert canvas.winfo_rooty() + canvas.winfo_height() <= view.chips_frame.winfo_rooty()
            assert view.chips_frame.winfo_rooty() + view.chips_frame.winfo_height() <= view.img_tray.winfo_rooty()
            assert view.img_tray.winfo_rooty() + view.img_tray.winfo_height() < view.input_textbox.winfo_rooty()
            if view.params_visible:
                assert view.params_frame.winfo_rooty() + view.params_frame.winfo_height() <= canvas.winfo_rooty()


def test_activity_is_folded_and_complete_output_is_inspectable(chat):
    root, view, service = chat
    stream = send(view, service)
    emit(root, stream, AgentEventType.REASONING_DELTA, content="Birinci düşünce. ")
    emit(root, stream, AgentEventType.REASONING_DELTA, content="İkinci düşünce.")
    emit(root, stream, AgentEventType.TEXT_DELTA, content="Sahneyi hazırlıyorum.")
    output = "Sonuç satırı\n" * 1000 + "SON SATIR"
    for index in (1, 2):
        emit(root, stream, AgentEventType.TOOL_CALL_STARTED, tool_name="run_command",
             arguments={"command": "API_KEY=secret-token python scene.py"})
        emit(root, stream, AgentEventType.TOOL_CALL_RESULT, tool_name="run_command", content=f"{index}: {output}")
    emit(root, stream, AgentEventType.TEXT_DELTA, content="Sahne hazır.")
    emit(root, stream, AgentEventType.DONE, content="Sahne hazır.")
    stream["on_done"]("Sahne hazır.")
    pump(root)
    group = view._current_activity
    assert len(view.messages) == 2  # DONE plus on_done must complete only once.
    assert view.current_bot_bubble.raw_content == "Sahneyi hazırlıyorum.\n\nSahne hazır."
    assert "düşünce" not in view.current_bot_bubble.raw_content
    assert not group.is_expanded
    assert not group.details_frame.winfo_ismapped()
    assert "2 işlem" in group.toggle_btn.cget("text")
    group.toggle_btn.invoke()
    group.reasoning_btn.invoke()
    tool = group.tools[1]
    tool.toggle_btn.invoke()
    pump(root)
    assert group.reasoning_text.get("1.0", "end-1c") == "Birinci düşünce. İkinci düşünce."
    assert tool.output_text.get("1.0", "end-1c") == f"2: {output}"
    assert "secret-token" not in tool.args_text.get("1.0", "end-1c")
    assert tool.output_text.winfo_height() <= 180
    tool._copy_output()
    assert root.clipboard_get() == f"2: {output}"
    group.toggle_btn.invoke()
    pump(root)
    assert not tool.winfo_ismapped()
    assert view.current_bot_bubble.text_label.winfo_ismapped()
    group.toggle_btn.invoke()
    pump(root)
    assert tool.is_expanded
    assert "SON SATIR" in tool.output_text.get("1.0", "end")


def test_errors_and_repeated_calls_keep_their_own_details(chat):
    root, view, service = chat
    stream = send(view, service)
    for call_id in ("a", "b"):
        emit(root, stream, AgentEventType.TOOL_CALL_STARTED, tool_name="fetch",
             server_name="mcp", metadata={"tool_call_id": call_id})
    emit(root, stream, AgentEventType.TOOL_CALL_ERROR, tool_name="fetch", server_name="mcp",
         content="İkinci çağrı başarısız", metadata={"tool_call_id": "b"})
    emit(root, stream, AgentEventType.TOOL_CALL_RESULT, tool_name="fetch", server_name="mcp",
         content="İlk çağrı başarılı", metadata={"tool_call_id": "a"})
    group = view._current_activity
    assert group.tools[0].output_content == "İlk çağrı başarılı"
    assert group.tools[1].error_content == "İkinci çağrı başarısız"
    emit(root, stream, AgentEventType.MCP_ERROR, server_name="other", content="Bağlantı kesildi")
    emit(root, stream, AgentEventType.ERROR, content="Model bağlantısı kesildi")
    stream["on_done"]("")
    pump(root)
    assert "2 hata" in group.toggle_btn.cget("text")
    assert "Model bağlantısı kesildi" in view.current_bot_bubble.raw_content
    assert len(view.messages) == 2
    assert not view.is_streaming
    assert not group.is_expanded


def test_cancel_and_clear_ignore_late_callbacks(chat):
    root, view, service = chat
    old = send(view, service)
    emit(root, old, AgentEventType.TOOL_CALL_STARTED, tool_name="slow_command")
    group = view._current_activity
    view._on_send_pressed()  # Stop
    assert group.tools[0].status == "stopped"
    assert "Durduruldu" in group.toggle_btn.cget("text")
    assert len(view.messages) == 2
    new = send(view, service, "Yeni mesaj")
    emit(root, old, AgentEventType.TEXT_DELTA, content="ESKİ YANIT")
    old["on_done"]("ESKİ YANIT")
    pump(root)
    assert view.current_bot_bubble.raw_content == "Yanıt hazırlanıyor..."
    assert view.is_streaming
    emit(root, new, AgentEventType.TEXT_DELTA, content="Yeni yanıt")
    view.clear_chat()
    emit(root, new, AgentEventType.DONE, content="GEÇ GELEN YANIT")
    new["on_error"]("GEÇ GELEN HATA")
    pump(root)
    assert not view.messages
    assert view.current_bot_bubble is None
    assert view._welcome_card.winfo_exists()
    assert service.cancelled == 2


def test_stream_follows_bottom_but_preserves_reading_position(chat):
    root, view, service = chat
    stream = send(view, service)
    emit(root, stream, AgentEventType.TEXT_DELTA, content="Satır\n" * 100)
    pump(root, 0.08)
    canvas = view.chat_scroll._parent_canvas
    assert canvas.yview()[1] > 0.99
    emit(root, stream, AgentEventType.TEXT_DELTA, content="Yeni satır\n" * 20)
    pump(root, 0.08)
    assert canvas.yview()[1] > 0.99
    canvas.yview_moveto(0.2)
    previous_top = canvas.canvasy(0)
    emit(root, stream, AgentEventType.TEXT_DELTA, content="Son satır\n" * 20)
    pump(root, 0.08)
    assert abs(canvas.canvasy(0) - previous_top) <= 2
    assert canvas.yview()[1] < 0.8
    canvas.yview_moveto(1.0)
    emit(root, stream, AgentEventType.DONE, content="Tamamlandı.")
    pump(root, 0.08)
    assert canvas.yview()[1] > 0.99


def test_text_only_reply_has_no_activity_and_on_done_fallback_works(chat):
    root, view, service = chat
    stream = send(view, service)
    stream["on_done"]("Merhaba!")
    pump(root)
    assert view.current_bot_bubble.raw_content == "Merhaba!"
    assert view._current_activity is None
    assert len(view.messages) == 2


def test_stream_completion_does_not_repeat_text_with_trailing_whitespace(chat):
    root, view, service = chat
    stream = send(view, service)
    emit(root, stream, AgentEventType.TEXT_DELTA, content="Yanıt.\n\n")
    emit(root, stream, AgentEventType.DONE, content="Yanıt.\n\n")
    assert view.current_bot_bubble.raw_content == "Yanıt."


@pytest.mark.parametrize("mode", ["Light", "Dark"])
def test_activity_and_message_fit_with_display_scaling(chat, mode):
    root, view, service = chat
    ctk.set_appearance_mode(mode)
    ctk.set_widget_scaling(1.25)
    try:
        stream = send(view, service)
        emit(root, stream, AgentEventType.TOOL_CALL_STARTED,
             tool_name="mcp_blender_" + "uzun_araç_adı_" * 15, server_name="blender")
        emit(root, stream, AgentEventType.TEXT_DELTA, content="Uzun yanıt metni. " * 30)
        group = view._current_activity
        group.toggle_btn.invoke()
        group.tools[0].toggle_btn.invoke()
        pump(root)
        user, bot = messages(view)
        assert user.text_label.cget("text_color") == "#ffffff"
        assert bot.text_label.cget("wraplength") * 1.25 <= bot.winfo_width() - 25
        assert group.tools[0].toggle_btn.winfo_rootx() + group.tools[0].toggle_btn.winfo_width() <= bot.winfo_rootx() + bot.winfo_width()
    finally:
        ctk.set_widget_scaling(1)
        ctk.set_appearance_mode("Dark")


def test_new_chat_preserves_history_and_reopened_chat_can_continue(chat):
    root, view, service = chat
    first = send(view, service, "İlk sohbet")
    emit(root, first, AgentEventType.TOOL_CALL_STARTED, tool_name="run_command", arguments={"command": "pwd"})
    emit(root, first, AgentEventType.TOOL_CALL_RESULT, tool_name="run_command", content="/workspace")
    emit(root, first, AgentEventType.DONE, content="İlk yanıt")
    first_id = view.session.session_id
    view.new_chat()
    assert view.session.session_id != first_id
    assert not view.messages
    second = send(view, service, "İkinci sohbet")
    emit(root, second, AgentEventType.DONE, content="İkinci yanıt")
    assert len(service.list_chat_history()) == 2
    label = next(label for label, session_id in view._history_ids.items() if session_id == first_id)
    view._select_history(label)
    pump(root)
    assert view.session.session_id == first_id
    assert [row["content"] for row in view.messages] == ["İlk sohbet", "İlk yanıt"]
    assert [message.content for message in view.session.messages] == ["İlk sohbet", "İlk yanıt"]
    assert len(service.streams) == 2  # Restoring never invokes the agent or tools.
    bot = messages(view)[1]
    from evren_agent.ui.components.tool_card import ToolActivityGroup
    group = next(child for child in bot.winfo_children() if isinstance(child, ToolActivityGroup))
    assert not group.is_expanded
    assert group.tools[0].output_content == "/workspace"
    assert group.tools[0].status == "done"
    followup = send(view, service, "Devam et")
    assert followup["session_id"] == first_id
    emit(root, followup, AgentEventType.DONE, content="Devam yanıtı")
    assert len(service.list_chat_history()) == 2
    assert [row["content"] for row in service.load_chat_transcript(first_id)] == ["İlk sohbet", "İlk yanıt", "Devam et", "Devam yanıtı"]


def test_restart_recovers_partial_reply_and_folded_activity(chat):
    root, view, service = chat
    stream = send(view, service, "Yarım kalan sohbet")
    emit(root, stream, AgentEventType.TEXT_DELTA, content="Kısmi yanıt")
    emit(root, stream, AgentEventType.TOOL_CALL_STARTED, tool_name="slow_command")
    pump(root, 0.8)
    saved = service.load_chat_transcript(view.session.session_id)
    assert saved[1]["content"] == "Kısmi yanıt"
    assert saved[1]["pending"]
    view.destroy()
    reopened_service = ChatServiceStub(service.chat_history.path)
    reopened = ChatView(root, reopened_service)
    reopened.pack(fill="both", expand=True)
    try:
        pump(root)
        assert reopened.session.session_id == stream["session_id"]
        assert "Kısmi yanıt" in reopened.messages[1]["content"]
        assert "Yanıt kesildi" in reopened.messages[1]["content"]
        assert not reopened.is_streaming
        assert not reopened_service.streams
        from evren_agent.ui.components.tool_card import ToolActivityGroup
        bot = messages(reopened)[1]
        group = next(child for child in bot.winfo_children() if isinstance(child, ToolActivityGroup))
        assert not group.is_expanded
        assert group.tools[0].status == "stopped"
    finally:
        reopened.destroy()


def test_deletion_requires_confirmation_and_removes_only_current_chat(chat, monkeypatch):
    root, view, service = chat
    first = send(view, service, "Korunacak sohbet")
    emit(root, first, AgentEventType.DONE, content="Korunacak yanıt")
    first_id = view.session.session_id
    view.new_chat()
    second = send(view, service, "Silinecek sohbet")
    emit(root, second, AgentEventType.DONE, content="Silinecek yanıt")
    second_id = view.session.session_id
    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *args: False)
    view._delete_chat()
    assert len(service.list_chat_history()) == 2
    monkeypatch.setattr("tkinter.messagebox.askyesno", lambda *args: True)
    view._delete_chat()
    assert [row["session_id"] for row in service.list_chat_history()] == [first_id]
    assert service.chat_history.load(second_id) is None
    assert not view.messages


def test_failed_save_keeps_current_chat_visible(chat, monkeypatch):
    root, view, service = chat
    stream = send(view, service)
    emit(root, stream, AgentEventType.DONE, content="Kaybolmaması gereken yanıt")
    session_id = view.session.session_id
    def fail(*args):
        raise OSError("Disk full")
    monkeypatch.setattr(service, "save_chat_transcript", fail)
    view.new_chat()
    assert view.session.session_id == session_id
    assert view.messages[-1]["content"] == "Kaybolmaması gereken yanıt"
    assert view.history_status.cget("text") == "Kaydedilemedi"


def test_async_model_list_preserves_restored_model(chat, monkeypatch):
    root, view, service = chat
    stream = send(view, service)
    emit(root, stream, AgentEventType.DONE, content="Yanıt")
    view.model_combo.set("saved-model")
    view._save_history()
    session_id = view.session.session_id
    view.new_chat()
    view._restore_chat(session_id)
    callbacks = []
    monkeypatch.setattr(service, "fetch_models_async", lambda on_success: callbacks.append(on_success))
    view._load_models()
    callbacks[0](["other-model"])
    assert view.model_combo.get() == "saved-model"
    assert view.session.model == "saved-model"


def test_saved_image_preview_survives_original_file_removal(chat, tmp_path):
    from PIL import Image
    root, view, service = chat
    image = tmp_path / "attached.png"
    Image.new("RGB", (40, 40), "blue").save(image)
    view.attached_image_path = str(image)
    stream = send(view, service, "Görseli incele")
    emit(root, stream, AgentEventType.DONE, content="Görsel yanıtı")
    session_id = view.session.session_id
    view.new_chat()
    image.unlink()
    view._restore_chat(session_id)
    pump(root)
    user = messages(view)[0]
    image_labels = [child for child in user.winfo_children()
                    if isinstance(child, ctk.CTkLabel) and child.cget("image") is not None]
    assert len(image_labels) == 1
    assert user.raw_content == "Görseli incele"

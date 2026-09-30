"""UI tests for Evren Agent Projects Workspace View."""
import tempfile
from pathlib import Path
import pytest

from evren_agent.ui.app import EvrenApp
from evren_agent.ui.views.projects_view import ProjectsView


def test_projects_view_full_lifecycle(monkeypatch):
    monkeypatch.setattr("tkinter.messagebox.showinfo", lambda *a, **k: None)
    monkeypatch.setattr("tkinter.messagebox.showwarning", lambda *a, **k: None)
    monkeypatch.setattr("tkinter.messagebox.showerror", lambda *a, **k: None)

    with tempfile.TemporaryDirectory() as tmpdir:

        tmp_path = Path(tmpdir)
        (tmp_path / "main.py").write_text("class TestClass:\n    pass\n")

        app = EvrenApp()
        streams = []
        monkeypatch.setattr(app.service, "chat_agent_stream_async", lambda **kwargs: streams.append(kwargs))
        try:
            # 1. Switch to projects view
            app.show_view("projects")
            assert app.active_tab == "projects"
            pv: ProjectsView = app.views["projects"]
            assert isinstance(pv, ProjectsView)

            # 2. Create a test project via service
            proj = pv.project_service.create_project(
                name="UI Test Project",
                local_path=str(tmp_path),
                description="Testing GUI interactions",
                template="Web Application",
            )
            assert proj is not None

            # 3. Refresh list and check project rendering
            pv.refresh_projects_list()
            cards = pv.cards_scroll.winfo_children()
            assert len(cards) >= 1

            # 4. Open workspace screen
            pv.show_workspace_screen(proj.id)
            assert pv.current_project_id == proj.id
            assert pv.workspace_container.winfo_ismapped() or pv.workspace_container.winfo_manager() != ""

            # 5. Switch between all workspace tabs
            sub_tabs = [
                "overview", "coding", "tasks", "features", "backlog",
                "roadmap", "bugs_debt", "docs_adr", "memory", "search_ask", "ai_pm", "settings"
            ]
            for tab_name in sub_tabs:
                pv._switch_workspace_tab(tab_name)
                assert pv.active_workspace_tab == tab_name
                # Workspace body should have rendered child widgets
                assert len(pv.workspace_body.winfo_children()) >= 1

            # 6. Test 'Start with Agent'
            tasks = pv.project_service.db.list_tasks(proj.id)
            assert len(tasks) >= 1
            pv._start_task_with_agent(tasks[0].id)
            assert pv.active_workspace_tab == "coding"
            assert "GÖREV BAŞLATILDI" in pv.coding_chat_box.get("1.0", "end")

            assert len(streams) == 1
            from evren_agent.core.events import AgentEvent, AgentEventType
            call = streams[-1]
            call["on_event"](AgentEvent(session_id=call["session_id"], type=AgentEventType.TEXT_DELTA, content="Plan hazır."))
            call["on_event"](AgentEvent(session_id=call["session_id"], type=AgentEventType.DONE, content="Plan hazır."))
            call["on_done"]("Plan hazır.")
            assert pv.coding_chat_box.get("1.0", "end").count("Plan hazır.") == 1
            assert not pv._coding_state()["busy"]
            pv.coding_input.insert(0, "Devam et")
            app.update()
            pv.coding_input.focus_force()
            app.update()
            app.focus_get().event_generate("<Return>")
            app.update()
            assert len(streams) == 2
            assert pv.coding_input.get() == ""
            pv.coding_input.insert(0, "Bekleyen talimat")
            app.focus_get().event_generate("<Return>")
            app.update()
            assert len(streams) == 2
            assert pv.coding_input.get() == "Bekleyen talimat"
            assert streams[-1]["session_id"] == call["session_id"]
            pv._switch_workspace_tab("overview")
            streams[-1]["on_error"]("Bağlantı kesildi")
            pv._switch_workspace_tab("coding")
            assert "Bağlantı kesildi" in pv.coding_chat_box.get("1.0", "end")
            assert not pv._coding_state()["busy"]
            pv.coding_input.insert(0, "Sayısal Enter")
            pv.coding_input.focus_force()
            app.update()
            # Windows Tk maps both Enter keys to Return; KP_Enter has no native
            # keycode there, so generating it does not dispatch a key event.
            keypad_enter = "<Return>" if app.tk.call("tk", "windowingsystem") == "win32" else "<KP_Enter>"
            app.focus_get().event_generate(keypad_enter)
            app.update()
            assert len(streams) == 3
            assert streams[-1]["prompt"] == "Sayısal Enter"
            streams[-1]["on_done"]("Tamamlandı")
            for width in (940, 1120, 1600):
                app.geometry(f"{width}x760")
                app.update()
                app.update_idletasks()
                assert pv.coding_input.winfo_width() > 150
                assert pv.coding_send_btn.winfo_rootx() + pv.coding_send_btn.winfo_width() <= app.winfo_rootx() + app.winfo_width()
                for button in pv.tab_buttons.values():
                    assert button.winfo_rootx() + button.winfo_width() <= app.winfo_rootx() + app.winfo_width()

            # 7. Test PM Check action
            pv._run_pm_check_action()
            checks = pv.project_service.db.list_checks(proj.id)
            assert len(checks) >= 1

            # 8. Return to list screen
            pv.show_list_screen()
            assert pv.list_container.winfo_ismapped() or pv.list_container.winfo_manager() != ""

        finally:
            app.destroy()

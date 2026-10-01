.PHONY: install setup test test-ui clean run commands ui gui help

help:
	@echo "EVREN CLI & Agent — Make Commands:"
	@echo "  make install   - Run installer (sets up .venv, deps, and commands)"
	@echo "  make test      - Run full pytest test suite"
	@echo "  make test-ui   - Run UI unit tests"
	@echo "  make run       - Launch interactive evren-agent REPL"
	@echo "  make commands  - List all available slash commands"
	@echo "  make ui        - Launch desktop UI application (GUI)"
	@echo "  make gui       - Alias for make ui"
	@echo "  make clean     - Remove caches and build artifacts"

install:
	@python3 install.py || python install.py

setup: install

test:
	@.venv/bin/pytest || .venv/Scripts/pytest.exe

test-ui:
	@.venv/bin/pytest tests/test_ui*.py || .venv/Scripts/pytest.exe tests/test_ui*.py

run:
	@.venv/bin/evren-agent || .venv/Scripts/evren-agent.exe

commands:
	@.venv/bin/evren-agent --commands || .venv/Scripts/evren-agent.exe --commands

ui:
	@.venv/bin/evren-gui $(ARGS) || .venv/Scripts/evren-gui.exe $(ARGS)

gui: ui

clean:
	rm -rf .pytest_cache build dist *.egg-info __pycache__ */__pycache__ */*/__pycache__

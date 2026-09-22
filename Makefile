.PHONY: install setup test clean run commands help

help:
	@echo "EVREN CLI & Agent — Make Commands:"
	@echo "  make install   - Run installer (sets up .venv, deps, and .env)"
	@echo "  make test      - Run full pytest test suite"
	@echo "  make run       - Launch interactive evren-agent REPL"
	@echo "  make commands  - List all available slash commands"
	@echo "  make clean     - Remove caches and build artifacts"

install:
	@python3 install.py || python install.py

setup: install

test:
	@.venv/bin/pytest || .venv/Scripts/pytest.exe

run:
	@.venv/bin/evren-agent || .venv/Scripts/evren-agent.exe

commands:
	@.venv/bin/evren-agent --commands || .venv/Scripts/evren-agent.exe --commands

clean:
	rm -rf .pytest_cache build dist *.egg-info __pycache__ */__pycache__ */*/__pycache__

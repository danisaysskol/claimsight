# ClaimSight Makefile (Linux/macOS + CI). Windows users: use run.ps1.
PY := .venv/bin/python
ifeq ($(OS),Windows_NT)
	PY := .venv/Scripts/python.exe
endif

.PHONY: help setup up down generate ingest quality dbt reporting pipeline dashboard excel test lint all

help:
	@echo "Tasks: setup up down generate ingest quality dbt reporting pipeline dashboard excel test lint all"

setup:
	python -m venv .venv
	$(PY) -m pip install --upgrade pip
	$(PY) -m pip install -r requirements.txt

up:
	docker compose up -d

down:
	docker compose down

generate:
	$(PY) -m claimsight.generate.generate

ingest:
	$(PY) -m claimsight.ingest.ingest

quality:
	$(PY) -m claimsight.quality.run_quality

reporting:
	$(PY) -m claimsight.reporting.build_reporting

dbt:
	cd dbt/claimsight_dw && $(PY) -m dbt build

excel:
	$(PY) -m claimsight.export.excel_report

pipeline:
	$(PY) -m claimsight.pipeline

dashboard:
	$(PY) -m streamlit run dashboard/app.py

test:
	$(PY) -m pytest -q

lint:
	$(PY) -m ruff check src tests dashboard

all: up pipeline dbt reporting excel test

CONDA ?= /Users/mengren/opt/anaconda3/bin/conda
ENV_NAME ?= microstructure
PYTHON ?= python

.PHONY: help install run report results test clean

help:
	@echo "Targets:"
	@echo "  make install  - install package in editable mode in $(ENV_NAME)"
	@echo "  make run      - run baseline simulation"
	@echo "  make report   - run simulation and save JSON for notebook analysis"
	@echo "  make results  - export portfolio PNG charts to results/"
	@echo "  make test     - run pytest"
	@echo "  make clean    - remove common Python cache files"

install:
	$(CONDA) run -n $(ENV_NAME) $(PYTHON) -m pip install -e .

run:
	$(CONDA) run -n $(ENV_NAME) env PYTHONPATH=src $(PYTHON) scripts/run_backtest.py --config configs/baseline_mm.json

report:
	$(CONDA) run -n $(ENV_NAME) env PYTHONPATH=src $(PYTHON) scripts/run_backtest.py --config configs/baseline_mm.json --output outputs/baseline_mm_result.json

results: report
	$(CONDA) run -n $(ENV_NAME) env MPLCONFIGDIR=/tmp/matplotlib-cache XDG_CACHE_HOME=/tmp $(PYTHON) scripts/export_results_charts.py

test:
	$(CONDA) run -n $(ENV_NAME) pytest -q

clean:
	find . -type d -name "__pycache__" -prune -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

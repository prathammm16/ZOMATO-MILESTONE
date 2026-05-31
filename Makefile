# Zomato AI Restaurant Recommendation System — Makefile
# Windows: use `make` from Git Bash, or run commands directly from README.

.PHONY: install test test-all demo demo-mock ui react-install react-ui react-vite react-build api api-mock api-server api-server-railway clean

install:
	pip install -r requirements.txt

test:
	python -m pytest -v -m "not integration"

test-all:
	python -m pytest -v

demo:
	python scripts/demo.py

demo-mock:
	python scripts/demo.py --mock

ui:
	streamlit run src/ui/app.py

react-install:
	cd frontend && npm install

react-ui:
	cd frontend && python -m http.server 5173 --bind 127.0.0.1

react-vite:
	cd frontend && npm run dev

react-build:
	cd frontend && npm run build

api-server:
	uvicorn src.api.server:app --host 0.0.0.0 --port 8000 --reload

api-server-railway:
	uvicorn src.api.server:app --host 0.0.0.0 --port $${PORT:-8000}

api:
	python -m src.api --location Bangalore --budget medium

api-mock:
	python -m src.api --mock --location Bangalore --budget medium

clean:
	python -c "import shutil, pathlib; [shutil.rmtree(p, ignore_errors=True) for p in pathlib.Path('.').rglob('__pycache__')]"

.PHONY: dev install format lint clean

dev:
	source venv/bin/activate && streamlit run app.py

install:
	python3 -m venv venv
	source venv/bin/activate && pip install -r requirements.txt

format:
	source venv/bin/activate && black src/ main.py app.py

lint:
	source venv/bin/activate && flake8 src/ main.py app.py

clean:
	rm -rf __pycache__
	rm -rf src/__pycache__
	rm -rf data/processed/*

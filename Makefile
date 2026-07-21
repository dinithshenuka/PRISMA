.PHONY: dev clean

venv/bin/activate: requirements.txt
	python3 -m venv venv
	./venv/bin/pip install -r requirements.txt
	touch venv/bin/activate

dev: venv/bin/activate
	./venv/bin/python src/prisma_cli.py

clean:
	rm -rf venv

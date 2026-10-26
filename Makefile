.PHONY: init run test golden openapi clean

init:
	.venv/bin/python scripts/init_db.py
	.venv/bin/python scripts/evaluate_golden.py --write

run:
	PYTHONPATH=src .venv/bin/uvicorn neuro_smetchik.api:app --host 0.0.0.0 --port 8000 --reload

test:
	.venv/bin/pytest -q

golden:
	.venv/bin/python scripts/evaluate_golden.py --report

openapi:
	.venv/bin/python scripts/export_openapi.py

clean:
	rm -f data/*.db data/*.db-wal data/*.db-shm

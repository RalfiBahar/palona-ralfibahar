run:
	uvicorn app.main:app --reload --port 8000

db.init:
	alembic revision --autogenerate -m "init"

db.upgrade:
	alembic upgrade head

ingest:
	python -m app.ingest --path ../data/catalog.sample.json --with-images=false

catalog.gen:
	python ../scripts/generate_catalog_from_fakestore.py --out ../data/catalog.sample.json

ingest.images:
	python -m app.ingest --path ../data/catalog.sample.json --with-images=true

test:
	pytest -q



install:
	pip install -r requirements.txt

run-api:
	uvicorn src.citegraph.api.main:app --reload

run-frontend:
	npm --prefix frontend run dev

run-dashboard:
	streamlit run dashboard/app.py

run-grobid:
	docker compose up -d grobid

run-neo4j:
	docker compose --profile neo4j up -d neo4j

test:
	pytest

format:
	black src dashboard tests scripts

lint:
	flake8 src dashboard tests scripts

demo:
	python scripts/demo.py

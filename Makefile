format:
	uv run ruff format

lint:
	uv run ruff check .

fix:
	uv run ruff check --fix .

run:
	uv run uvicorn app.main:app --reload

# Clean up the project including _pycache_
clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name ".DS_Store" -exec rm -rf {} +
	find . -type d -name ".vscode" -exec rm -rf {} +

# Run PGVector
pgvector:
	docker run -d \
  		-e POSTGRES_DB=ai \
  		-e POSTGRES_USER=ai \
  		-e POSTGRES_PASSWORD=ai \
		-e PGDATA=/var/lib/postgresql/data/pgdata \
		-v pgvolume:/var/lib/postgresql/data \
		-p 5532:5432 \
		--name pgvector \
		agnohq/pgvector:16

# Stop PGVector
pgvector-stop:
	docker stop pgvector

run-chatbot:
	uv run python -m chatbot.agentic_chatbot


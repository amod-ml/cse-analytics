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
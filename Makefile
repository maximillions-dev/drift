.PHONY: test check clean install

install:
	pip install pyyaml
	pip install -e .

test:
	python -m pytest tests/ -v --tb=short

check:
	drift check

clean:
	rm -rf .pytest_cache
	rm -rf build dist
	rm -rf src/*.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name '*.pyc' -delete

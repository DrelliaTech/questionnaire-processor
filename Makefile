.PHONY: help install test lint format clean deploy

help:  ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install:  ## Install dependencies
	pip install -r requirements.txt
	pip install -e .

install-dev:  ## Install development dependencies
	pip install -r requirements.txt
	pip install -e ".[dev]"

test:  ## Run tests
	pytest tests/

lint:  ## Run linting
	flake8 .
	mypy .

format:  ## Format code
	black .

format-check:  ## Check code formatting
	black --check .

clean:  ## Clean up build artifacts
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

deploy-dev:  ## Deploy to development environment
	cd deployment && npm install && npm run deploy:dev

deploy-prod:  ## Deploy to production environment
	cd deployment && npm install && npm run deploy:prod

remove:  ## Remove deployed resources
	cd deployment && npm run remove

logs:  ## View Lambda logs (specify function with FUNC=functionName)
	cd deployment && npm run logs -- -f $(FUNC)

package:  ## Build deployment package
	python setup.py sdist bdist_wheel
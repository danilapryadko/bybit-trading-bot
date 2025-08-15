.PHONY: help
help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

.PHONY: install
install: ## Install dependencies
	pip install -r requirements.txt

.PHONY: dev
dev: ## Start development environment
	docker-compose up -d
	@echo "Waiting for services to be healthy..."
	@sleep 5
	@echo "Services started:"
	@echo "  PostgreSQL: localhost:5432"
	@echo "  Redis: localhost:6379"
	@echo "  Prometheus: http://localhost:9090"
	@echo "  Grafana: http://localhost:3000 (admin/admin)"

.PHONY: stop
stop: ## Stop development environment
	docker-compose down

.PHONY: clean
clean: ## Clean development environment
	docker-compose down -v
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	rm -f *.log

.PHONY: test
test: ## Run tests
	python -m pytest tests/ -v

.PHONY: test-coverage
test-coverage: ## Run tests with coverage
	python -m pytest --cov=. --cov-report=html tests/

.PHONY: lint
lint: ## Run code quality checks
	python -m flake8 . --exclude=venv,__pycache__
	python -m black --check .

.PHONY: format
format: ## Format code
	python -m black .

.PHONY: run
run: ## Run trading bot
	python main.py

.PHONY: run-testnet
run-testnet: ## Run trading bot on testnet
	python main.py --testnet

.PHONY: backtest
backtest: ## Run backtest
	python -m scripts.backtest

.PHONY: db-init
db-init: ## Initialize database
	python scripts/init_db.py

.PHONY: db-migrate
db-migrate: ## Run database migrations
	python scripts/migrate_db.py

.PHONY: logs
logs: ## Show logs
	docker-compose logs -f

.PHONY: shell
shell: ## Open Python shell with project context
	python -i scripts/shell_context.py

.PHONY: monitor
monitor: ## Open monitoring dashboards
	@echo "Opening monitoring dashboards..."
	@echo "Prometheus: http://localhost:9090"
	@echo "Grafana: http://localhost:3000 (admin/admin)"
	@open http://localhost:3000 2>/dev/null || xdg-open http://localhost:3000 2>/dev/null || echo "Please open http://localhost:3000 manually"

.PHONY: check-api
check-api: ## Check Bybit API connection
	python bybit_client.py

.PHONY: check-strategy
check-strategy: ## Test strategies without trading
	python strategies.py

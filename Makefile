# Build scripts to run commands within the Docker container or create local environments

# Docker variables
RUN_IN_NEW_WEBCONTEXT = docker compose run -it splitter_api
EXEC_IN_WEB = docker compose run splitter_api

#  General
##############################################

initial_install: create_docker_networks build run

build: ## build the stack
	@echo Building from file. './docker-compose.yml.'
	docker compose build

run: ## start the stack
	@echo Running from file. './docker-compose.yml.'
	docker compose up

run_and_build: ## Build and then start the stack
	@echo Building containers and running from file. './docker-compose.yml.'
	docker compose up --build

stop: ## Stop containers
	@echo Stopping containers.
	docker compose down

clear_docker_volumes: ## clear docker volumes
	check_clean_db
	@echo Stopping and removing containers.
	docker compose down -v

check_clean_db: ## clear docker vols
	@echo -n "This will clear local docker volumes before running tests. Are you sure? [y/N] " && read ans && [ $${ans:-N} = y ]

format: ## Use pre-commit config to format files
	pre-commit run --all-files

create_docker_networks:
	docker network create mor_bridge_network

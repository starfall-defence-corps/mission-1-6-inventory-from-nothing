SHELL := /bin/bash
ROOT_DIR := $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))

.PHONY: doctor setup test submit reset destroy shell rotate help

help: ## Show available commands
	@echo ""
	@echo "=============================================="
	@echo "  STARFALL DEFENCE CORPS ACADEMY"
	@echo "  Mission 1.6: Inventory from Nothing"
	@echo "=============================================="
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}'
	@echo ""

doctor: ## Check your machine is mission-ready (Docker, port 2221, tools)
	@bash $(ROOT_DIR)/scripts/doctor.sh

setup: ## Power up the range (recon node + hidden fleet)
	@bash $(ROOT_DIR)/scripts/setup-lab.sh

shell: ## Board the recon node (sdc-ops) — run nmap + ansible from here
	@docker exec -it -u cadet -w /home/cadet/workspace sdc-ops /bin/bash

test: ## Ask ARIA to verify your work
	@bash $(ROOT_DIR)/scripts/check-work.sh

rotate: ## (advanced) Force Nyx to rotate the fleet's addressing now
	@bash $(ROOT_DIR)/scripts/rotate-lab.sh

submit: ## Submit your work for ARIA review (branch, commit, push, PR)
	@bash $(ROOT_DIR)/scripts/submit.sh

reset: ## Tear down and rebuild the range (re-randomises addressing)
	@bash $(ROOT_DIR)/scripts/reset-lab.sh

destroy: ## Tear down everything (containers, keys, range state, venv)
	@bash $(ROOT_DIR)/scripts/destroy-lab.sh

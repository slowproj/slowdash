
SLOWDASH_DIR = $(shell pwd)
SLOWDASH_BIN = "$(SLOWDASH_DIR)/bin/slowdash"
SLOWDASH_ENV = "$(SLOWDASH_DIR)/bin/slowdash-bashrc"
GIT = $(shell which git)


all:
	@if [ ! -f "$(SLOWDASH_DIR)/app/site/jagaimo/jagaimo.mjs" ]; then \
		if [ x$(GIT) = x ]; then \
			echo 'submodules not cloned, git command not available'; \
			exit 255; \
		fi; \
		$(GIT) submodule update --init --recursive; \
		if [ ! -f "$(SLOWDASH_DIR)/app/site/jagaimo/jagaimo.mjs" ]; then \
			echo 'unable obtain to submodules'; \
			exit 255; \
		fi; \
		echo "submodules updated"; \
		echo ""; \
	fi

	@if [ ! -d "$(SLOWDASH_DIR)/bin" ]; then mkdir "$(SLOWDASH_DIR)/bin"; fi

	@echo '#! /bin/bash' > $(SLOWDASH_BIN)
	@echo '' >> $(SLOWDASH_BIN)
	@echo 'SLOWDASH_DIR="$(SLOWDASH_DIR)"' >> $(SLOWDASH_BIN)
	@echo '' >> $(SLOWDASH_BIN)
	@echo 'if [ -d "$$SLOWDASH_DIR/venv" ]; then' >> $(SLOWDASH_BIN)
	@echo '   source "$$SLOWDASH_DIR/venv/bin/activate"' >> $(SLOWDASH_BIN)
	@echo '   echo Running in venv at "$$SLOWDASH_DIR/venv" >&2' >> $(SLOWDASH_BIN)
	@echo 'fi' >> $(SLOWDASH_BIN)
	@echo '' >> $(SLOWDASH_BIN)
	@echo 'use_slowdog=0' >> $(SLOWDASH_BIN)
	@echo 'args=()' >> $(SLOWDASH_BIN)
	@echo 'for arg in "$$@"; do' >> $(SLOWDASH_BIN)
	@echo '    if [[ "$$arg" == "--slowdog" ]]; then' >> $(SLOWDASH_BIN)
	@echo '        use_slowdog=1' >> $(SLOWDASH_BIN)
	@echo '    else' >> $(SLOWDASH_BIN)
	@echo '        args+=("$$arg")' >> $(SLOWDASH_BIN)
	@echo '    fi' >> $(SLOWDASH_BIN)
	@echo 'done' >> $(SLOWDASH_BIN)
	@echo '' >> $(SLOWDASH_BIN)
	@echo 'if [[ $$use_slowdog = 1 ]];  then' >> $(SLOWDASH_BIN)
	@echo '    python3 $$SLOWDASH_DIR/utils/slowdog.py $$SLOWDASH_DIR/app/server/slowdash.py "$${args[@]}"' >> $(SLOWDASH_BIN)
	@echo 'else' >> $(SLOWDASH_BIN)
	@echo '    python3 "$$SLOWDASH_DIR/app/server/slowdash.py" "$${args[@]}"' >> $(SLOWDASH_BIN)
	@echo 'fi' >> $(SLOWDASH_BIN)
	@echo '' >> $(SLOWDASH_BIN)
	@chmod 755 $(SLOWDASH_BIN)

	@echo 'export PATH="$(SLOWDASH_DIR)/bin:$$PATH"' > $(SLOWDASH_ENV)
	@echo 'export PYTHONPATH="$(SLOWDASH_DIR)/lib/slowpy:$$PYTHONPATH"' >> $(SLOWDASH_ENV)

	@ln -fs "$(SLOWDASH_DIR)/docs" "$(SLOWDASH_DIR)/app/site"
	@if [ -d .git/hooks ]; then ln -fs ../../.git-hooks/pre-commit .git/hooks; fi

	@echo "## Installation successful ##"
	@echo ""
	@echo "- Executable files are copied to $(SLOWDASH_DIR)/bin."
	@echo "- Set enviromnental variables for the slowdash executables and Python modules by: "
	@echo "  source $(SLOWDASH_DIR)/bin/slowdash-bashrc"
	@echo ""
	@echo '- To build docker images, run "make docker"'
	@echo '- To setup Python venv for SlowDash, run "make setup-venv"'


setup-venv:
	./utils/slowdash-setup-venv.sh


docker:
	docker rmi -f slowdash slowpy-notebook
	docker build -t slowdash .
	docker build -t slowpy-notebook -f ./lib/Dockerfile ./lib


update:
	git pull --recurse-submodules
	@echo ''
	@make --no-print-directory


docker-image-update:
	docker rmi -f slowproj/slowdash slowproj/slowpy-notebook

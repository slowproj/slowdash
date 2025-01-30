
SLOWDASH_DIR = $(shell pwd)
SLOWDASH_BIN = "$(SLOWDASH_DIR)/bin/slowdash"
SLOWDASH_ENV = "$(SLOWDASH_DIR)/bin/slowdash-bashrc"
PYTHON = $(shell which python3)
GIT = $(shell which git)


all:
	@if [ x$(PYTHON) = x ]; then \
		echo 'unable to find python3 (`which python3` returned null)'; \
		exit 255; \
	fi

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
	@echo '    $(PYTHON) $(SLOWDASH_DIR)/utils/slowdog.py $(SLOWDASH_DIR)/app/server/slowdash.py "$${args[@]}"' >> $(SLOWDASH_BIN)
	@echo 'else' >> $(SLOWDASH_BIN)
	@echo '    $(PYTHON) "$(SLOWDASH_DIR)/app/server/slowdash.py" "$${args[@]}"' >> $(SLOWDASH_BIN)
	@echo 'fi' >> $(SLOWDASH_BIN)
	@echo '' >> $(SLOWDASH_BIN)
	@chmod 755 $(SLOWDASH_BIN)

	@echo 'export PATH="$$PATH:$(SLOWDASH_DIR)/bin"' > $(SLOWDASH_ENV)
	@echo 'export PYTHONPATH="$$PYTHONPATH:$(SLOWDASH_DIR)/lib/slowpy"' >> $(SLOWDASH_ENV)

	@ln -fs "$(SLOWDASH_DIR)/docs" "$(SLOWDASH_DIR)/app/site"

	@echo "## Installation successful"
	@echo ""
	@echo "- Executable files are copied to $(SLOWDASH_DIR)/bin."
	@echo "- Set enviromnental variables for the slowdash executables and Python modules by: "
	@echo "  source $(SLOWDASH_DIR)/bin/slowdash-bashrc"
	@echo '- To build docker images, run "make docker"'


docker: all
	docker rmi -f slowdash slowpy-notebook
	docker build -t slowdash .
	docker build -t slowpy-notebook -f ./lib/Dockerfile ./lib


update:
	git pull --recurse-submodules
	@make


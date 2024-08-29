
SLOWDASH_DIR = $(shell pwd)
SLOWDASH_BIN = $(SLOWDASH_DIR)/bin/slowdash
SLOWDASH_ENV = $(SLOWDASH_DIR)/bin/slowdash-bashrc
PYTHON = $(shell which python3)
GIT = $(shell which git)


all:
	@if [ x$(PYTHON) = x ]; then \
		echo 'unable to find python3 (`which python3` returned null)'; \
		exit 255; \
	fi

	@if [ ! -f $(SLOWDASH_DIR)/main/web/jagaimo/jagaimo.mjs ]; then \
		if [ x$(GIT) = x ]; then \
			echo 'submodules not cloned, git command not available'; \
			exit 255; \
		fi; \
		$(GIT) submodule update --init --recursive; \
		if [ ! -f $(SLOWDASH_DIR)/main/web/jagaimo/jagaimo.mjs ]; then \
			echo 'unable obtain to submodules'; \
			exit 255; \
		fi; \
		echo "submodules updated"; \
		echo ""; \
	fi

	@if [ ! -d $(SLOWDASH_DIR)/bin ]; then mkdir $(SLOWDASH_DIR)/bin; fi

	@echo '#! /bin/sh' > $(SLOWDASH_BIN)
	@echo '' >> $(SLOWDASH_BIN)
	@echo '$(PYTHON) $(SLOWDASH_DIR)/main/server/slowdash.py "$$@"' >> $(SLOWDASH_BIN)
	@chmod 755 $(SLOWDASH_BIN)

	@echo 'export PATH=$$PATH:$(SLOWDASH_DIR)/bin' > $(SLOWDASH_ENV)
	@echo 'export PYTHONPATH=$$PYTHONPATH:$(SLOWDASH_DIR)/lib/slowpy' >> $(SLOWDASH_ENV)

	@ln -fs $(SLOWDASH_DIR)/docs $(SLOWDASH_DIR)/main/web

	@echo "## Installation successful"
	@echo ""
	@echo "- Executable files are copied to $(SLOWDASH_DIR)/bin."
	@echo "- Set enviromnental variables for the slowdash executables and Python modules by: "
	@echo "  source $(SLOWDASH_DIR)/bin/slowdash-bashrc"
	@echo '- To create a docker image, run "make docker"'


docker: all
	docker rmi -f slowdash
	docker build -t slowdash .

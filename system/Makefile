
SLOWDASH_DIR = $(shell cd ..; pwd)
SLOWDASH_BIN = $(SLOWDASH_DIR)/bin/slowdash
SLOWDASH_ENV = $(SLOWDASH_DIR)/bin/slowdash-bashrc
PYTHON = $(shell which python3)
GIT = $(shell which git)


all:
	@if [ x$(PYTHON) = x ]; then \
		echo 'unable to find python3 (`which python3` returned null)'; \
		exit 255; \
	fi

	@if [ ! -f $(SLOWDASH_DIR)/system/web/jagaimo/jagaimo.mjs ]; then \
		if [ x$(GIT) = x ]; then \
			echo 'submodules not cloned, git command not available'; \
			exit 255; \
		fi; \
		$(GIT) submodule update --init --recursive; \
		if [ ! -f $(SLOWDASH_DIR)/system/web/jagaimo/jagaimo.mjs ]; then \
			echo 'unable obtain to submodules'; \
			exit 255; \
		fi; \
		echo "submodules updated"; \
		echo ""; \
	fi

	@if [ ! -d $(SLOWDASH_DIR)/bin ]; then mkdir $(SLOWDASH_DIR)/bin; fi

	@echo '#! /bin/sh' > $(SLOWDASH_BIN)
	@echo '' >> $(SLOWDASH_BIN)
	@echo '$(PYTHON) $(SLOWDASH_DIR)/system/server/slowdash.py "$$@"' >> $(SLOWDASH_BIN)
	@chmod 755 $(SLOWDASH_BIN)

	@echo 'export PATH=$$PATH:$(SLOWDASH_DIR)/bin' > $(SLOWDASH_ENV)
	@echo 'export PYTHONPATH=$(SLOWDASH_DIR)/lib/slowpy:$$PYTHONPATH' >> $(SLOWDASH_ENV)

	@ln -fs $(SLOWDASH_DIR)/docs $(SLOWDASH_DIR)/system/web

	@if [ -f $(SLOWDASH_DIR)/ExampleProjects/QuickTour/generate-testdata.py ]; then \
		cat $(SLOWDASH_DIR)/ExampleProjects/QuickTour/generate-testdata.py > $(SLOWDASH_DIR)/docs/generate-testdata.py.txt; \
	fi

	@echo "Make successful"
	@echo ""
	@echo "- executable files are copied to $(SLOWDASH_DIR)/bin"
	@echo "- including this bin directory to your PATH variable might be useful, either by"
	@echo '    export PATH=$${PATH}:$(SLOWDASH_DIR)/bin'
	@echo '        or'
	@echo '    source $(SLOWDASH_DIR)/bin/slowdash-bashrc'

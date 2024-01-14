
SLOWDASH_DIR = $(shell cd ..; pwd)
SLOWDASH_BIN = $(SLOWDASH_DIR)/bin/slowdash
SLOWDASH_ENV = $(SLOWDASH_DIR)/bin/slowdash-bashrc
PYTHON = $(shell which python3)


all:
	@if [ x$(PYTHON) = x ]; then \
		echo 'unable to find python3 (`which python3` returned null)'; \
		exit 255; \
	fi

	@if [ ! -d $(SLOWDASH_DIR)/bin ]; then mkdir $(SLOWDASH_DIR)/bin; fi

	@echo '#! /bin/sh' > $(SLOWDASH_BIN)
	@echo '' >> $(SLOWDASH_BIN)
	@echo '$(PYTHON) $(SLOWDASH_DIR)/system/server/slowdash.py "$$@"' >> $(SLOWDASH_BIN)
	@chmod 755 $(SLOWDASH_BIN)

	@echo 'export PATH=$$PATH:$(SLOWDASH_DIR)/bin' >> $(SLOWDASH_ENV)
	@echo 'export PYTHONPATH=$(SLOWDASH_DIR)/system/client:$$PYTHONPATH' >> $(SLOWDASH_ENV)

	@cat $(SLOWDASH_DIR)/ExampleProjects/QuickTour/generate-testdata.py > $(SLOWDASH_DIR)/docs/generate-testdata.py.txt
	@ln -fs $(SLOWDASH_DIR)/docs $(SLOWDASH_DIR)/system/web

	@echo "Make successful"
	@echo ""
	@echo "- executable files are copied to $(SLOWDASH_DIR)/bin"
	@echo "- including this bin dir to your PATH might be useful, either by"
	@echo '    export PATH=$${PATH}:$(SLOWDASH_DIR)/bin'
	@echo '        or'
	@echo '    source $(SLOWDASH_DIR)/bin/slowdash-bashrc'


SLOWDASH_DIR = $(shell pwd)
SLOWDASH_BIN = "$(SLOWDASH_DIR)/bin/slowdash"
SLOWDASH_ENV = "$(SLOWDASH_DIR)/bin/slowdash-bashrc"
GIT = $(shell which git)

PIP_REQS = uvicorn hypercorn websockets pyyaml psutil bcrypt requests 
PIP_OPTIONAL_DBS = mysql-connector-python aiomysql influxdb-client redis pymongo couchdb elasticsearch
PIP_OPTIONAL_MSGS = pika aio-pika paho-mqtt aiomqtt
PIP_OPTIONAL_DEVS = pyserial pyvisa pymodbus
PIP_OPTIONAL_DATA = numpy matplotlib lmfit scikit-image scikit-learn


all: venv-install slowdash venv-setup print-success

without-venv: slowdash print-success



slowdash:
	@if [ ! -f "$(SLOWDASH_DIR)/app/site/slowjs/jagaimo/jagaimo.mjs" ]; then \
		if [ x$(GIT) = x ]; then \
			echo 'submodules not cloned, git command not available'; \
			exit 255; \
		fi; \
		$(GIT) submodule update --init --recursive; \
		if [ ! -f "$(SLOWDASH_DIR)/app/site/slowjs/jagaimo/jagaimo.mjs" ]; then \
			echo 'unable obtain to submodules'; \
			exit 255; \
		fi; \
		echo "submodules updated"; \
		echo ""; \
	fi

	@if [ ! -d "$(SLOWDASH_DIR)/bin" ]; then mkdir "$(SLOWDASH_DIR)/bin"; fi
	@if [ -d .git/hooks ]; then ln -fs ../../.git-hooks/pre-commit .git/hooks; fi

	@echo '#! /bin/bash' > $(SLOWDASH_BIN)
	@echo '' >> $(SLOWDASH_BIN)
	@echo 'SLOWDASH_DIR="$(SLOWDASH_DIR)"' >> $(SLOWDASH_BIN)
	@echo '' >> $(SLOWDASH_BIN)
	@echo 'if [ -d "$$SLOWDASH_DIR/venv" ]; then' >> $(SLOWDASH_BIN)
	@echo '   echo Running in venv at "$$SLOWDASH_DIR/venv" >&2' >> $(SLOWDASH_BIN)
	@echo '   source "$$SLOWDASH_DIR/venv/bin/activate"' >> $(SLOWDASH_BIN)
	@echo 'else' >> $(SLOWDASH_BIN)
	@echo '   echo Running without venv' >> $(SLOWDASH_BIN)
	@echo '   export PYTHONPATH="$$SLOWDASH_DIR/lib/slowpy:$$PYTHONPATH"' >> $(SLOWDASH_BIN)
	@echo '   export PYTHONPATH="$$SLOWDASH_DIR/lib/slowlette:$$PYTHONPATH"' >> $(SLOWDASH_BIN)
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

	@echo 'export SLOWDASH_DIR=$(SLOWDASH_DIR)' > $(SLOWDASH_ENV)
	@echo 'alias slowdash="$$SLOWDASH_DIR/bin/slowdash"' >> $(SLOWDASH_ENV)
	@echo 'alias slowdash-activate-venv="source $$SLOWDASH_DIR/venv/bin/activate"' >> $(SLOWDASH_ENV)

	@echo "generating requirements.txt..."
	@echo "# SlowDash requirements #" > requirements.txt
	@for pkg in $(PIP_REQS); do echo $$pkg >> requirements.txt; done
	@echo "-e ./lib/slowpy" >> requirements.txt
	@echo "-e ./lib/slowlette" >> requirements.txt
	@echo "" >> requirements.txt
	@echo "### OPTIONAL Database packages, necessary only when used ###" >> requirements.txt
	@if command -v pg_config > /dev/null; then \
		echo psycopg2 >> requirements.txt; \
		echo asyncpg >> requirements.txt; \
	fi
	@if command -v mysql_config > /dev/null; then \
		echo mysqlclient >> requirements.txt; \
	fi
	@for pkg in $(PIP_OPTIONAL_DBS); do echo $$pkg >> requirements.txt; done
	@echo "" >> requirements.txt
	@echo "### OPTIONAL Messaging system packages, necessary only when used ###" >> requirements.txt
	@for pkg in $(PIP_OPTIONAL_MSGS); do echo $$pkg >> requirements.txt; done
	@echo "" >> requirements.txt
	@echo "### OPTIONAL Device access packages, necessary only when used ###" >> requirements.txt
	@for pkg in $(PIP_OPTIONAL_DEVS); do echo $$pkg >> requirements.txt; done
	@echo "" >> requirements.txt
	@echo "### OPTIONAL data analysis/processing packages users might use ###" >> requirements.txt
	@for pkg in $(PIP_OPTIONAL_DATA); do echo $$pkg >> requirements.txt; done


venv-install:
	python3 -m venv venv


venv-setup:
	@echo "setting up venv..."
	@if [ -d ./venv ]; then . venv/bin/activate; pip install -r requirements.txt; deactivate; fi


print-success:
	@echo ""
	@echo ""
	@echo "### SlowDash Installation is successful ###"
	@echo "- Executable files are copied to $(SLOWDASH_DIR)/bin."
	@echo "- Python venv is created/updated at $(SLOWDASH_DIR)/venv."
	@echo '- Run below to enable the "slowdash" command:'
	@echo "    source $(SLOWDASH_DIR)/bin/slowdash-bashrc"
	@echo ""
	@echo '- To activate SlowDash venv, run "slowdash-activate-venv"'
	@echo '- To build docker images, run "make docker"'


update:
	git pull --recurse-submodules
	@echo ''
	@make --no-print-directory


docker:
	docker rmi -f slowdash slowpy-notebook
	docker build -t slowdash .
	docker build -t slowpy-notebook -f ./lib/slowpy/Dockerfile ./lib/slowpy

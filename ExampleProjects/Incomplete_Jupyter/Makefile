
jupyter-slowpy:
	docker rmi -f slowpy-notebook
	docker build -t slowpy-notebook -f ../../lib/Dockerfile ../../lib

	@if [ ! -d notebook ]; then mkdir notebook; fi

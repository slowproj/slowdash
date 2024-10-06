
jupyter-slowpy:
	docker rmi -f slowpy-notebook
	docker build --build-arg BASE_IMAGE=jupyter/scipy-notebook:latest -t slowpy-notebook -f ../../lib/Dockerfile ../../lib

	@if [ ! -d notebook ]; then mkdir notebook; fi

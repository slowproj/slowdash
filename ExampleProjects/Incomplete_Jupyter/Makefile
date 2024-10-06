
jupyter-slowpy:
	docker rmi -f jupyter-slowpy
	docker build --build-arg BASE_IMAGE=jupyter/scipy-notebook:latest -t jupyter-slowpy -f ../../lib/Dockerfile ../../lib

	@if [ ! -d notebook ]; then mkdir notebook; fi

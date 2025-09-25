
slowdash-dripline:
	docker rmi -f slowdash-dripline	
	docker build --build-arg BASE_IMAGE=ghcr.io/driplineorg/dripline-python:v5.1.0 -t slowdash-dripline -f ../../Dockerfile ../..

with-honeybee:
	docker rmi -f slowdash-dripline
	docker build --build-arg BASE_IMAGE=dripline-honeybee -t slowdash-dripline -f ../../Dockerfile ../..

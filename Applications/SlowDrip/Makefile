
slowdash-dripline:
	docker rmi -f slowdash-dripline	
	docker build --build-arg BASE_IMAGE=driplineorg/dripline-python:v4.7.1 -t slowdash-dripline -f ../../Dockerfile ../..

with-honeybee:
	docker rmi -f slowdash-dripline
	docker build --build-arg BASE_IMAGE=dripline-honeybee -t slowdash-dripline -f ../../Dockerfile ../..

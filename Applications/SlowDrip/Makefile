
slowdash-dripline:
	docker rmi -f slowdash-dripline
	env BASE_IMAGE=driplineorg/dripline-python:v4.5.8 \
	docker build --build-arg BASE_IMAGE=driplineorg/dripline-python:v4.5.8 -t slowdash-dripline -f ../../Dockerfile ../..

with-honeybee:
	docker rmi -f slowdash-dripline
	env BASE_IMAGE=dripline-honeybee \
	docker build --build-arg BASE_IMAGE=dripline-honeybee -t slowdash-dripline -f ../../Dockerfile ../..

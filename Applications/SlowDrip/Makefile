
slowdash-dripline:
	docker rmi -f slowdash-dripline
	env BASE_IMAGE=driplineorg/dripline-python:v4.5.8 \
	docker build -t slowdash-dripline -f ../../Dockerfile ../..

with-honeybee:
	docker rmi -f slowdash-dripline
	env BASE_IMAGE=dripline-honeybee \
	docker build -t slowdash-dripline -f ../../Dockerfile ../..

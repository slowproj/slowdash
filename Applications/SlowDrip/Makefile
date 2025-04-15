
slowdash-dripline:
	docker rmi -f slowdash-dripline	
#	docker build --build-arg BASE_IMAGE=driplineorg/dripline-python:develop -t slowdash-dripline -f ../../Dockerfile ../..
	docker build --build-arg BASE_IMAGE=mydl -t slowdash-dripline -f ../../Dockerfile ../..

with-honeybee:
	docker rmi -f slowdash-dripline
	docker build --build-arg BASE_IMAGE=dripline-honeybee -t slowdash-dripline -f ../../Dockerfile ../..

FROM fnproject/python:3.9
WORKDIR /function
ADD . /function/
RUN pip install -no-cache-dir requests oci
CMD ["handler.handler"]


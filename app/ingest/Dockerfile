FROM fnproject/python:3.9
WORKDIR /function
ADD . /function/
RUN pip install --no-cache-dir fdk mysql-connector-python langchain langchain-openai
CMD ["handler.handler"]

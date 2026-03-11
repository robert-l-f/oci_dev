FROM python:3.9-slim

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir streamlit requests oci

EXPOSE 8501

CMD ["streamlit", "run", "handler.py", "--server.port=8501", "--server.address=0.0.0.0"]

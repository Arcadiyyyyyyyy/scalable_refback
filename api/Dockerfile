FROM python:3.11 as python-base
COPY requirements.txt .
RUN pip install -r requirements.txt
FROM python-base as modules-base
COPY . .
CMD [ "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "80" ]
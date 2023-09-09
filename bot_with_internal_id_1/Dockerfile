FROM python:3.11 as python-base
COPY requirements.txt .
RUN pip install -r requirements.txt
FROM python-base as modules-base
COPY . .
CMD [ "python", "__main__.py" ]
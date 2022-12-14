# base image
FROM python:3.8.12-buster

# copy api
COPY api /api

# copy requirements.txt
COPY requirements.txt /requirements.txt

# run pip
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

# run uvicorn server
CMD uvicorn api.fast:app --host 0.0.0.0 --port $PORT

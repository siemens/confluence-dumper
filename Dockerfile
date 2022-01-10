# syntax=docker/dockerfile:1
FROM python:2.7
WORKDIR /app
RUN apt-get update -y
COPY packages.txt packages.txt
RUN xargs apt-get install -y < packages.txt
COPY requirements.txt requirements.txt
RUN pip install -r requirements.txt
COPY . .

CMD [ "python", "confluence_dumper.py"]

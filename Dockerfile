# syntax=docker/dockerfile:1
FROM python:3.10
WORKDIR /app
RUN apt-get update -y
COPY packages.txt packages.txt
RUN xargs apt-get install -y < packages.txt
COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt
COPY . .

CMD [ "python3", "confluence_dumper.py"]

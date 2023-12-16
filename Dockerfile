FROM python:3.9.2
# Install dependencies
RUN pip install poetry rich
ENV PYTHONUNBUFFERED=1
# Install Project 
RUN pip install "arkitekt[all]"

RUN mkdir /app
COPY . /app
WORKDIR /app

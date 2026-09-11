FROM python:{__python_version__}-slim

RUN pip install "arkitekt-next[all]>={__arkitekt_version__}"

RUN mkdir /app
WORKDIR /app
COPY .arkitekt_next /app/.arkitekt_next
COPY app.py /app/app.py

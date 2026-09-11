FROM python:{__python_version__}-slim

RUN pip install "arkitekt[all]>={__arkitekt_version__}"

RUN mkdir /app
WORKDIR /app
COPY .arkitekt /app/.arkitekt
COPY app.py /app/app.py

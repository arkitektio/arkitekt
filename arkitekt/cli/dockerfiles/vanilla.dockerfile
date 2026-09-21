FROM python:{__python_version__}-slim

RUN pip install "arkitekt[all]>={__arkitekt_version__}"

RUN mkdir /app
WORKDIR /app
# The whole project: the app target may be any module in it, not only app.py.
COPY . /app

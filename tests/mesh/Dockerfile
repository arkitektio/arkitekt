# The app the mesh test runs: arkitekt as a user installs it, and nothing else.
#
# The wheel is built from this checkout by the test. It is installed with no extras, so
# the mesh node can only have come from arkitekt's own dependencies. mikro is the service
# the app calls.
FROM python:3.13-slim

COPY wheels/ /wheels/
RUN pip install --no-cache-dir --disable-pip-version-check /wheels/arkitekt-*.whl mikro

COPY client.py /client.py
ENTRYPOINT ["python", "/client.py"]

FROM python:{__python_version__}-slim

RUN pip install "arkitekt[all]>={__arkitekt_version__}"

RUN mkdir /app
WORKDIR /app
# The whole project: the app target may be any module in it, not only app.py.
COPY . /app

# The version of this build, when it is not the one the source declares: a build from
# a branch is passed it by `arkitekt plugin release`. Empty for a release proper.
ARG ARKITEKT_APP_VERSION=""
ENV ARKITEKT_APP_VERSION=$ARKITEKT_APP_VERSION

FROM python:3.12-slim@sha256:f77ac9e44ae96ef2c90b8053ea08c31f8be030f824196b0ae4db6d462c84e51f
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
  && apt-get install -y --no-install-recommends gcc-arm-none-eabi binutils-arm-none-eabi gcc g++ git gcovr \
  && rm -rf /var/lib/apt/lists/*
COPY requirements.txt /opt/test-requirements.txt
RUN python -m pip install --disable-pip-version-check --no-compile --no-deps --only-binary=:all: --require-hashes -r /opt/test-requirements.txt

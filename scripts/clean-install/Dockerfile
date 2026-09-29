# Clean Linux machine for walking the documented Coga install path.
#
# Python 3.11 is the declared floor. Only the `coga/install` prerequisites
# Coga itself needs are added: git, and uv (the documented installer). No
# agent CLI, gh, or op: the attended steps install and log in to those.
# Coga is never preinstalled; `walk.sh` installs the artifact under test.
FROM python:3.11-slim

ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl git \
    && rm -rf /var/lib/apt/lists/* \
    && python -m pip install --no-cache-dir uv

RUN useradd --create-home --shell /bin/bash tester
COPY walk.sh /usr/local/bin/coga-walk
RUN chmod 0755 /usr/local/bin/coga-walk

USER tester
WORKDIR /home/tester
ENV PATH=/home/tester/.local/bin:$PATH

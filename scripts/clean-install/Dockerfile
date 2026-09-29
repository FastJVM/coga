FROM python:3.11-slim-bookworm

RUN sed -i 's|http://deb.debian.org|https://deb.debian.org|g' /etc/apt/sources.list.d/debian.sources \
    && apt-get update -o APT::Update::Error-Mode=any \
    && apt-get install -y --no-install-recommends git ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN python -m pip install --no-cache-dir uv \
    && useradd --create-home --uid 1000 --shell /bin/bash coga

# Keep uv on the declared Python floor, even if a release needs a newer Python.
ENV PATH="/home/coga/.local/bin:${PATH}" \
    UV_PYTHON=/usr/local/bin/python3.11 \
    UV_PYTHON_DOWNLOADS=never

COPY container.sh /usr/local/bin/coga-clean-install
RUN chmod 755 /usr/local/bin/coga-clean-install
USER coga
WORKDIR /home/coga
CMD ["sleep", "infinity"]

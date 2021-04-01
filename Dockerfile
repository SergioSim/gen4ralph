# -- Base image --
FROM python:3.9-slim as base

# Upgrade pip to its latest release to speed up dependencies installation
RUN apt update && apt upgrade -y && pip install --upgrade pip

# -- Builder --
FROM base as builder

WORKDIR /build

COPY . /build/
    
RUN python setup.py install

# -- Core --
FROM base as core

COPY --from=builder /usr/local /usr/local

WORKDIR /app


# -- Development --
FROM core as development

# Copy all sources, not only runtime-required files
COPY . /app/

# Uninstall gen4ralph and re-install it in editable mode along with development
# dependencies
RUN pip uninstall -y gen4ralph
RUN pip install -e .[dev]

# Un-privileged user running the application
USER ${DOCKER_USER:-1000}


# -- Production --
FROM core as production

# Un-privileged user running the application
USER ${DOCKER_USER:-1000}

CMD ["gen4ralph"]

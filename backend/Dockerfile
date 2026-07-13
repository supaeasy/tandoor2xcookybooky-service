FROM texlive/texlive:latest

RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Make sure the recipe-related LaTeX packages are present regardless of the
# base image's texlive scheme.
RUN tlmgr update --self && \
    tlmgr install xcookybooky cookybooky lettrine nicefrac microtype \
        tex-gyre babel-swissgerman || true

WORKDIR /app

COPY requirements.txt .
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

COPY app ./app
COPY templates ./templates
COPY xcookybooky.cfg ./xcookybooky.cfg

EXPOSE 8080

CMD ["python3", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8080"]

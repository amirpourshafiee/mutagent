FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 TMPDIR=/tmp
RUN pip install --no-cache-dir pytest pytest-timeout pytest-cov mutmut==3.8.1
COPY pyproject.toml /opt/mutagent/pyproject.toml
COPY src /opt/mutagent/src
RUN pip install --no-cache-dir /opt/mutagent && useradd -m grader
USER grader
WORKDIR /tmp
ENTRYPOINT ["python", "-m", "mutagent.cli"]

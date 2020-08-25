FROM continuumio/miniconda3

WORKDIR /app

COPY environment.yml .
RUN conda env create --name env -f environment.yml

SHELL ["conda", "run", "-n", "env", "/bin/bash", "-c"]

RUN echo "Make sure psycopg2 is installed:"
RUN python -c "import psycopg2"

COPY ./app ./

ENTRYPOINT ["conda", "run", "-n", "env", "python", "main.py"]


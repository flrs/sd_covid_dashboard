FROM continuumio/miniconda3

WORKDIR /app

COPY environment.yml .
RUN conda env create --name env -f environment.yml

COPY ./app ./

ENTRYPOINT ["/bin/bash", "-c", "source activate env && python main.py"]


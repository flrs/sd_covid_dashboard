FROM continuumio/miniconda3

WORKDIR /app

ADD environment.yml /tmp/environment.yml
RUN conda env create -f /tmp/environment.yml --name env

RUN conda clean --all -y

# Pull the environment name out of the environment.yml
RUN echo "source activate env" > ~/.bashrc
ENV PATH /opt/conda/envs/env/bin:$PATH

COPY ./app.ipynb ./app.ipynb

COPY ./src ./src

EXPOSE 8866

ENTRYPOINT ["/bin/bash", "-c", "source activate env && voila app.ipynb --no-browser --port=8866 --enable_nbextensions=True --template vuetify-base --VoilaExecutePreprocessor.timeout=999 --debug"]

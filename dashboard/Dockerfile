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

COPY ./data/commit_hash.txt ./data/commit_hash.txt
COPY ./data/commit_msg.txt ./data/commit_msg.txt
COPY ./data/deploy_date.txt ./data/deploy_date.txt
COPY ./data/estimate_2019_zip_1600028105323.xlsx ./data/estimate_2019_zip_1600028105323.xlsx

EXPOSE 8866

ENTRYPOINT ["/bin/bash", "-c", "source activate env && voila app.ipynb --no-browser --port=8866 --enable_nbextensions=True --template vuetify-base --VoilaExecutePreprocessor.timeout=999 --MappingKernelManager.cull_interval=120 --MappingKernelManager.cull_idle_timeout=1200"]

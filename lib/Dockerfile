# Jupyter (w/ Scipy) with SlowPy

ARG BASE_IMAGE=jupyter/scipy-notebook
FROM ${BASE_IMAGE}

USER root
COPY slowpy "/home/${NB_USER}/slowpy"
RUN chown -R ${NB_USER}:${NB_GROUP} "/home/${NB_USER}/slowpy"

USER ${NB_USER}
RUN pip install --no-cache-dir "/home/${NB_USER}/slowpy" && fix-permissions "${CONDA_DIR}" && fix-permissions "/home/${NB_USER}"

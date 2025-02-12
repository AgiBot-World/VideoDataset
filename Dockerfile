ARG NVIDIA_PYTORCH_VERSION=24.03
FROM nvcr.io/nvidia/pytorch:${NVIDIA_PYTORCH_VERSION}-py3

ENV NVIDIA_DRIVER_CAPABILITIES ${NVIDIA_DRIVER_CAPABILITIES},video

WORKDIR /workspace
COPY . videodataset/
RUN cd videodataset/ && \
    python3 -m pip install --no-cache-dir .

CMD ["/bin/bash"]
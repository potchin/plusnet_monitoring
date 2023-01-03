#!/bin/bash
podman build -t  docker.io/jeffers/plusnet_monitoring:latest -t docker.io/jeffers/plusnet_monitoring:$(git rev-parse --short HEAD) .
podman push docker.io/jeffers/plusnet_monitoring:latest docker.io/jeffers/plusnet_monitoring:$(git rev-parse --short HEAD)
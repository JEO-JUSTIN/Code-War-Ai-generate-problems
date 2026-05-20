# ── Code Execution Engine Runtime Image ──────────────────────────────────────
# Contains: Python 3, GCC, OpenJDK 17
# Built once; reused for every ephemeral execution container.
# ─────────────────────────────────────────────────────────────────────────────

FROM ubuntu:22.04

# Prevent interactive prompts during package install
ENV DEBIAN_FRONTEND=noninteractive

# Install runtimes
RUN apt-get update && apt-get install -y --no-install-recommends \
        python3 \
        python3-pip \
        gcc \
        libc6-dev \
        openjdk-17-jdk-headless \
    && rm -rf /var/lib/apt/lists/*

# Create a non-root user for safer execution
RUN useradd -m -s /bin/bash runner

# Working directory mounted by the host at runtime
WORKDIR /workspace

# Drop to non-root user
USER runner

# Default: do nothing (commands supplied at docker run time)
CMD ["bash"]

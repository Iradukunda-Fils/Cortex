# Use official Coq image (pinned OS and OCaml/Coq environment)
FROM coqorg/coq:9.0-ocaml-4.14-flambda

LABEL maintainer="Cortex Formal Verification Team"
LABEL description="Reproducible evaluation container for Cortex spatiotemporal formalization."

# Set working directory inside container
WORKDIR /home/coq/cortex-verification

# Copy project configuration and verification source files
COPY --chown=coq:coq _CoqProject Makefile archive_logs.sh ./
COPY --chown=coq:coq *.v ./

# Ensure scripts have execution permissions
RUN chmod +x archive_logs.sh

# Default entrypoint: Run the full verification build and log audit
CMD ["./archive_logs.sh"]

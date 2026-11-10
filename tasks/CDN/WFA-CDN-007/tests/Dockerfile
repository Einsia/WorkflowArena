FROM workflowarena-cdc-avb-repurpose:20261005
# WorkflowArena CDC verifier image: same toolchain as the agent image; grader, rubric, answer key and a
# private copy of the public inputs live in /tests. Only /workspace/output is collected from the agent.
USER root
COPY . /tests/
RUN mkdir -p /workspace/output /logs/verifier
WORKDIR /workspace

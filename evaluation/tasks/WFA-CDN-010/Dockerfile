FROM workflowarena-original-cdc-tools:20261022
# WorkflowArena CDC verifier image: same toolchain as the agent image; grader, rubric, answer key and a
# private copy of the public inputs live in /tests. Only /workspace/output is collected from the agent.
USER root
COPY . /tests/
RUN python3 /tests/fetch/fetch_inputs.py --manifest /tests/fetch/sources.json --destination /tests/public_input && rm -rf /tests/fetch
RUN mkdir -p /workspace/output /logs/verifier
WORKDIR /workspace

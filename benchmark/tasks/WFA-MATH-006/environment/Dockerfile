FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates curl git aria2 zstd procps \
    && rm -rf /var/lib/apt/lists/*
ENV ELAN_HOME=/opt/elan PATH=/opt/elan/bin:$PATH
RUN set -eux; curl -sSfL --retry 8 --retry-delay 10 -o /tmp/elan.tgz \
      https://github.com/leanprover/elan/releases/download/v4.1.2/elan-x86_64-unknown-linux-gnu.tar.gz; \
    tar -xzf /tmp/elan.tgz -C /tmp; /tmp/elan-init -y --default-toolchain none --no-modify-path; \
    rm -f /tmp/elan.tgz /tmp/elan-init; elan --version
# Lean release pinned by the task's lean-toolchain; multi-connection download (the GitHub release CDN is
# slow per connection behind the build proxy), unpacked where elan looks for installed toolchains.
RUN set -eux; V=v4.27.0; D=$ELAN_HOME/toolchains/leanprover--lean4---$V; \
    aria2c -q -x 16 -s 16 -k 4M --max-tries=20 --retry-wait=15 -d /tmp -o lean.tar.zst \
      https://github.com/leanprover/lean4/releases/download/$V/lean-${V#v}-linux.tar.zst; \
    mkdir -p $D; tar -I zstd -xf /tmp/lean.tar.zst -C $D --strip-components=1; rm -f /tmp/lean.tar.zst; \
    $D/bin/lean --version
ADD workspace.tar.gz /workspace/
WORKDIR /workspace
RUN ln -s /workspace /testbed && git init -q -b main && printf '.lake/\n' >> .git/info/exclude && git add -A \
    && git -c user.name=wfs -c user.email=wfs@localhost commit -qm start
# Shallow-seed the pinned Mathlib checkout (a full clone of mathlib4 is several GB), then let lake fetch the rest.
RUN set -eux; set -- $(python3 -c 'import json; m = json.load(open("lake-manifest.json")); \
p = [p for p in m["packages"] if p["name"] == "mathlib"][0]; print(m.get("packagesDir", ".lake/packages"), p["url"], p["rev"])'); \
    d=$1/mathlib; mkdir -p $d; git -C $d init -q; git -C $d remote add origin $2; \
    ok=0; for i in 1 2 3 4 5; do if git -C $d fetch -q --depth 1 origin $3; then ok=1; break; fi; sleep 30; done; [ "$ok" = 1 ]; \
    git -C $d checkout -q --detach FETCH_HEAD; \
    ok=0; for i in 1 2 3 4 5; do if lake env true; then ok=1; break; fi; sleep 30; done; [ "$ok" = 1 ]
# BuildKit RUN steps default to a soft nofile limit of 1024: parallel .ltar unpacking then fails with EMFILE.
RUN set -eux; ulimit -n 262144; ok=0; for i in 1 2 3 4 5 6; do if lake exe cache get; then ok=1; break; fi; sleep 60; done; \
    [ "$ok" = 1 ]; rm -rf /root/.cache/mathlib
# Build the start state. Projects with warningAsError fail here on the target's own `sorry` only.
RUN ulimit -n 262144; lake build ConNF.Counting.Conclusions || echo "WFS: start build of ConNF.Counting.Conclusions did not succeed (see log)"

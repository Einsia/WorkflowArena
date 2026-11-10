#!/bin/bash
# Materialise the starting tree: remove the completion engine, keep its contract.
#
# Run during image build against a pristine source tree ($1).  What happens, in
# order:
#
#   1. the 22 files of the completion subsystem are hollowed out: every
#      declaration, type, trait impl, const, static, attribute and doc comment
#      stays, every function body becomes `todo!()`
#   2. the inline `#[cfg(test)] mod tests` blocks inside those files are
#      deleted.  They go with the implementation they test; the control runs
#      delete them from the reference tree too, so that both sides run exactly
#      the same suite
#   3. the tests that judge the engine are blanked out -- the file stays, with a
#      placeholder comment, so the `mod` declarations wiring them into their
#      test crates still compile.  The verifier copies the real contents back
#   4. `.git` goes, because `git checkout` would otherwise undo all of the above
#   5. dependencies are vendored, so the agent (which has no network) can build
#
# Two bodies are not `todo!()`, both recorded in the stub report:
#   * `CommandCompletion::get_executable_files` returns `impl Iterator`, and an
#     opaque return type has no hidden type to infer from `!`.  It becomes
#     `std::iter::empty()`.
#   * `impl Command for CommandlineComplete`'s `name`, `description`,
#     `signature`, `extra_description`, `search_terms` and `examples` are read
#     while the engine state is built (a command is indexed by `name()`), so a
#     panic there stops the shell from starting at all rather than stopping
#     completion from working, and nothing in the tree would run.  They are
#     declarative command metadata, so they are kept verbatim.
set -euo pipefail
TREE=${1:?usage: carve.sh <source-tree>}
HERE=$(cd "$(dirname "$0")" && pwd)

COMPLETIONS=crates/nu-cli/src/completions
CARVE_FILES="\
$COMPLETIONS/mod.rs $COMPLETIONS/base.rs $COMPLETIONS/completer.rs \
$COMPLETIONS/completion_common.rs $COMPLETIONS/completion_options.rs \
$COMPLETIONS/arg_value_completion.rs $COMPLETIONS/attribute_completions.rs \
$COMPLETIONS/cell_path_completions.rs $COMPLETIONS/command_completions.rs \
$COMPLETIONS/directory_completions.rs $COMPLETIONS/dotnu_completions.rs \
$COMPLETIONS/env_var_completions.rs $COMPLETIONS/exportable_completions.rs \
$COMPLETIONS/file_completions.rs $COMPLETIONS/flag_completions.rs \
$COMPLETIONS/operator_completions.rs $COMPLETIONS/static_completions.rs \
$COMPLETIONS/variable_completions.rs $COMPLETIONS/custom_completions/mod.rs \
$COMPLETIONS/custom_completions/input.rs $COMPLETIONS/custom_completions/output.rs \
crates/nu-cli/src/commands/commandline/complete.rs"

# Judging tests: blanked here, restored by the verifier.
HIDDEN_TESTS="crates/nu-cli/tests/completions/mod.rs \
tests/repl/test_commandline.rs \
tests/integration/completions.rs"
# Helpers used only by the judging tests; no `mod` declaration survives them,
# so the whole directory goes.
HIDDEN_SUPPORT="crates/nu-cli/tests/completions/support"

CL=crates/nu-cli/src/commands/commandline/complete.rs

echo "[carve] hollowing out the completion engine"
cat > /tmp/carve-overrides.json <<'JSON'
{"crates/nu-cli/src/completions/command_completions.rs":
 {"get_executable_files": "std::iter::empty()"}}
JSON
( cd "$TREE" && python3 -I "$HERE/stubgen_rs.py" --mode carve \
    --overrides /tmp/carve-overrides.json \
    --keep "$CL::name,$CL::description,$CL::signature,$CL::extra_description,$CL::search_terms,$CL::examples" \
    --report /tmp/carve-stub-report.json \
    $CARVE_FILES )
# Kept outside the tree: it names every hollowed function, which is evidence
# for us and not a hint for the agent.
mkdir -p /opt/carve && cp /tmp/carve-stub-report.json /opt/carve/stub-report.json

echo "[carve] blanking the judging tests (the mod wiring has to keep compiling)"
for f in $HIDDEN_TESTS; do
    test -f "$TREE/$f"
    printf '// Removed with the implementation under test.\n' > "$TREE/$f"
done
rm -rf "$TREE/$HIDDEN_SUPPORT"

echo "[carve] upstream's agent instructions are not this task's instructions"
rm -f "$TREE/CLAUDE.md" "$TREE/AGENTS.md"

echo "[carve] no VCS history in the tree (a checkout would undo the carve)"
rm -rf "$TREE/.git"
test ! -d "$TREE/.git"

echo "[carve] vendoring dependencies for an offline agent"
( cd "$TREE" && cargo vendor --locked vendor > /tmp/vendor-config.toml )
cat /tmp/vendor-config.toml >> "$TREE/.cargo/config.toml"
grep -q "vendored-sources" "$TREE/.cargo/config.toml"

echo "[carve] the tree must still compile, and its test binaries must still link"
( cd "$TREE" && cargo build --offline --locked --workspace )
( cd "$TREE" && cargo test --offline --locked --no-run -p nu-cli --test tests )
( cd "$TREE" && cargo test --offline --locked --no-run -p nu --test tests )
( cd "$TREE" && cargo test --offline --locked --no-run -p nu-lsp --lib )

echo "[carve] done"

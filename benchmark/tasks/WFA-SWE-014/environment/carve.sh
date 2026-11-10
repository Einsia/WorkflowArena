#!/bin/bash
# Materialise the starting tree: remove the model layer, keep its contract.
#
# Run during image build against a pristine source tree ($1).  Four things
# happen, in this order:
#
#   1. the eight files of the model / field / JSON-schema layer are hollowed
#      out -- every declaration stays, every function body is replaced by a
#      return of a zero value derived from the return annotation.
#      --descend-conditionals is required: three annotation helpers
#      (SkipJsonSchema, SerializeAsAny, ValidateAs) are declared in the
#      else-branch of an `if TYPE_CHECKING:` guard, and without it their class
#      bodies keep their implementation
#   2. the tests that judge that layer are removed (the verifier brings them
#      back after the agent has finished).  The tests of the retained modules
#      stay, so the tree is not silent
#   3. every __pycache__ is deleted -- a .pyc of the original module would hand
#      back the implementation to anyone who looks
#   4. the VCS history goes
#
# Zero values rather than `raise NotImplementedError`: pydantic builds every
# model class through a metaclass in the retained `pydantic/_internal` package,
# and that metaclass calls back into the carved files.  A raising stub would
# abort `import pydantic` itself, and the negative control would read as
# "nothing ran" instead of "everything failed" (BRIEF section 4).  With zero
# values the package still imports and 1063 of the hidden tests run and fail
# for real reasons.
set -euo pipefail
TREE=${1:?usage: carve.sh <source-tree>}
HERE=$(cd "$(dirname "$0")" && pwd)

CARVE_FILES="pydantic/main.py pydantic/fields.py pydantic/json_schema.py
pydantic/type_adapter.py pydantic/functional_validators.py
pydantic/functional_serializers.py pydantic/root_model.py pydantic/aliases.py"

HIDDEN_TESTS="tests/test_abc.py tests/test_aliases.py tests/test_annotated.py
tests/test_assert_in_validators.py tests/test_callable.py tests/test_computed_fields.py
tests/test_config.py tests/test_construction.py tests/test_create_model.py
tests/test_deprecated.py tests/test_deprecated_fields.py tests/test_dunder_all.py
tests/test_edge_cases.py tests/test_fields.py tests/test_json.py tests/test_json_schema.py
tests/test_main.py tests/test_meta.py tests/test_missing_sentinel.py
tests/test_model_signature.py tests/test_model_validator.py tests/test_parse.py
tests/test_pickle.py tests/test_private_attributes.py tests/test_rich_repr.py
tests/test_root_model.py tests/test_serialize.py tests/test_serialize_as_any.py
tests/test_strict.py tests/test_structural_pattern_matching.py tests/test_titles.py
tests/test_type_adapter.py tests/test_type_alias_type.py tests/test_type_hints.py
tests/test_types_typeddict.py tests/test_validators.py"

echo "[carve] hollowing out the model layer"
( cd "$TREE" && python3 -I "$HERE/stubgen.py" --descend-conditionals $CARVE_FILES )

echo "[carve] removing the judging tests"
( cd "$TREE" && rm -f $HIDDEN_TESTS )

echo "[carve] no VCS history in the tree (a checkout would undo the carve)"
rm -rf "$TREE/.git"
test ! -d "$TREE/.git"

echo "[carve] the carved tree must still import"
( cd "$TREE" && python3 -c '
import sys
sys.path.insert(0, ".")
import pydantic, pydantic.json_schema, pydantic.type_adapter, pydantic.dataclasses
print("[carve] pydantic", pydantic.VERSION, "imports with the layer removed")
try:
    class M(pydantic.BaseModel):
        x: int
except Exception as exc:
    print("[carve] defining a model fails, as it must:", type(exc).__name__)
else:
    raise SystemExit("[carve] a model can still be defined -- the carve did not take")
' )

# Last, so that nothing after this point can leave bytecode behind.  A .pyc of
# an original module would hand the implementation back to anyone who looks.
echo "[carve] removing compiled bytecode"
find "$TREE" -name '__pycache__' -type d -prune -exec rm -rf {} + 2>/dev/null || true
find "$TREE" -name '*.pyc' -delete 2>/dev/null || true
test -z "$(find "$TREE" -name '*.pyc' -print -quit)"

echo "[carve] done"

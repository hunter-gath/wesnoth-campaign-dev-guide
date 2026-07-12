The Rise of Wesnoth Developer Reference — bundled tools

trow_unit_dependency_audit.py
  Requires a local Wesnoth repository checkout.

  python3 tools/trow_unit_dependency_audit.py \
    --wesnoth-root /path/to/wesnoth \
    --output /tmp/trow-unit-closure.json \
    --strict

validate_reference.py
  Validates an extracted reference site.

  python3 tools/validate_reference.py /path/to/trow-developer-reference

Release baseline
  wesnoth/wesnoth commit 6ab3fc1af3e259515c9558564accd16c69800d62

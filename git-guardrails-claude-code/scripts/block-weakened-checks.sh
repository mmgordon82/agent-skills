#!/bin/bash
# Block the agent from weakening checks instead of fixing code:
# - git commit/push with --no-verify (or commit -n)
# - edits to existing lint/format/pre-commit configs
# Override for a legitimate config change: ALLOW_CONFIG_EDIT=1 in the environment.

INPUT=$(cat)
[ "$ALLOW_CONFIG_EDIT" = "1" ] && exit 0

COMMAND=$(echo "$INPUT" | jq -r '.tool_input.command // empty')
BARE=$(echo "$COMMAND" | sed -E "s/\"[^\"]*\"//g; s/'[^']*'//g")  # ignore quoted args (commit messages)
if [ -n "$COMMAND" ] && echo "$BARE" | grep -qE 'git[^|;&]*(--no-verify|commit[^|;&]* -n( |$))'; then
  echo "BLOCKED: '$COMMAND' skips git hooks. Fix the failing check instead." >&2
  exit 2
fi

FILE=$(echo "$INPUT" | jq -r '.tool_input.file_path // empty')
[ -z "$FILE" ] || [ ! -e "$FILE" ] && exit 0
case "$(basename "$FILE")" in
  .eslintrc*|eslint.config.*|.prettierrc*|prettier.config.*|biome.json|biome.jsonc|\
  ruff.toml|.ruff.toml|.flake8|.pylintrc|mypy.ini|.golangci.yml|.golangci.yaml|\
  .shellcheckrc|.hadolint.yaml|.yamllint|.yamllint.yaml|.markdownlint*|.stylelintrc*|\
  .editorconfig|.pre-commit-config.yaml)
    echo "BLOCKED: editing existing check config '$FILE'. Fix the code instead, or ask the user to rerun with ALLOW_CONFIG_EDIT=1." >&2
    exit 2 ;;
esac
exit 0

#!/usr/bin/env bash

set -euo pipefail

repo_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
artifact_dir="${1:-${repo_dir}/artifacts}"
version="$(node -p "require('${repo_dir}/package.json').version")"
staging_dir="$(mktemp -d)"
plugin_dir="${staging_dir}/LegionCenter"
artifact_path="${artifact_dir}/LegionCenter-${version}.tar.gz"

cleanup() {
  rm -rf "${staging_dir}"
}
trap cleanup EXIT

cd "${repo_dir}"
pnpm run build

mkdir -p "${plugin_dir}" "${artifact_dir}"
cp LICENSE README.md THIRD_PARTY_NOTICES.md main.py package.json plugin.json requirements.txt "${plugin_dir}/"
cp -R assets defaults dist py_modules "${plugin_dir}/"
find "${plugin_dir}" -type d -name __pycache__ -prune -exec rm -rf {} +
find "${plugin_dir}" -type f \( -name '*.pyc' -o -name '*.pyo' \) -delete

COPYFILE_DISABLE=1 tar --no-xattrs -czf "${artifact_path}" -C "${staging_dir}" LegionCenter
shasum -a 256 "${artifact_path}"

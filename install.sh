#!/usr/bin/env sh
# mlxer — Headless MLX Local LLM Server Manager
# Installs the mlxer CLI binary for managing local MLX language-model HTTP servers on Apple Silicon Macs.
# See: https://github.com/Pixie-sh/mlxer
set -eu

REPO="Pixie-sh/mlxer"
VERSION="${MLXER_VERSION:-latest}"
BIN_DIR="${MLXER_BIN_DIR:-$HOME/.local/bin}"
BIN_NAME="mlxer"
ARTIFACT="mlxer-darwin-arm64.tar.gz"

OS="$(uname -s)"
ARCH="$(uname -m)"

if [ "$OS" != "Darwin" ] || [ "$ARCH" != "arm64" ]; then
  echo "mlxer standalone binaries currently support macOS Apple Silicon only." >&2
  echo "Use pipx instead: pipx install mlxer" >&2
  exit 1
fi

for cmd in awk curl grep install shasum tar; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "$cmd is required to install mlxer." >&2
    exit 1
  fi
done

if [ "$VERSION" = "latest" ]; then
  BASE_URL="https://github.com/$REPO/releases/latest/download"
else
  BASE_URL="https://github.com/$REPO/releases/download/$VERSION"
fi

TMP_DIR="$(mktemp -d)"
cleanup() {
  rm -rf "$TMP_DIR"
}
trap cleanup EXIT INT TERM

ARCHIVE="$TMP_DIR/$ARTIFACT"
CHECKSUMS="$TMP_DIR/checksums.txt"

if ! curl -fsL "$BASE_URL/$ARTIFACT" -o "$ARCHIVE"; then
    echo "Failed to download mlxer from $BASE_URL." >&2
  echo "The requested release asset may not exist yet. Use pipx instead: pipx install mlxer" >&2
  exit 1
fi

if ! curl -fsL "$BASE_URL/checksums.txt" -o "$CHECKSUMS"; then
    echo "Failed to download checksums.txt from $BASE_URL." >&2
  echo "The requested mlxer release may be missing checksum assets." >&2
  exit 1
fi

EXPECTED="$(grep "  $ARTIFACT$" "$CHECKSUMS" | awk '{print $1}')"
if [ -z "$EXPECTED" ]; then
  echo "No checksum entry found for $ARTIFACT." >&2
  exit 1
fi

ACTUAL="$(shasum -a 256 "$ARCHIVE" | awk '{print $1}')"
if [ "$ACTUAL" != "$EXPECTED" ]; then
  echo "Checksum verification failed for $ARTIFACT." >&2
  exit 1
fi

ARCHIVE_LIST="$TMP_DIR/archive-list.txt"
tar -tzf "$ARCHIVE" > "$ARCHIVE_LIST"
if [ "$(wc -l < "$ARCHIVE_LIST" | tr -d ' ')" != "1" ] || ! grep -qx "$BIN_NAME" "$ARCHIVE_LIST"; then
    echo "Unexpected archive contents in the mlxer release." >&2
  exit 1
fi

tar -xzf "$ARCHIVE" -C "$TMP_DIR" "$BIN_NAME"
if [ ! -f "$TMP_DIR/$BIN_NAME" ]; then
    echo "Archive did not contain the mlxer binary." >&2
  exit 1
fi
mkdir -p "$BIN_DIR"
install -m 0755 "$TMP_DIR/$BIN_NAME" "$BIN_DIR/$BIN_NAME"

case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *) echo "Note: $BIN_DIR is not on PATH. Add it before running $BIN_NAME." >&2 ;;
esac

echo "Installed $BIN_NAME to $BIN_DIR/$BIN_NAME"
echo "Next: $BIN_NAME doctor"

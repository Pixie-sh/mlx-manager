#!/usr/bin/env sh
set -eu

REPO="Pixie-sh/mlx-manager"
VERSION="${MLX_MANAGER_VERSION:-latest}"
BIN_DIR="${MLX_MANAGER_BIN_DIR:-$HOME/.local/bin}"
ARTIFACT="mlx-manager-darwin-arm64.tar.gz"

OS="$(uname -s)"
ARCH="$(uname -m)"

if [ "$OS" != "Darwin" ] || [ "$ARCH" != "arm64" ]; then
  echo "mlx-manager standalone binaries currently support macOS Apple Silicon only." >&2
  echo "Use pipx instead: pipx install mlx-manager" >&2
  exit 1
fi

for cmd in awk curl grep install shasum tar; do
  if ! command -v "$cmd" >/dev/null 2>&1; then
    echo "$cmd is required to install mlx-manager." >&2
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
  echo "Failed to download $ARTIFACT from $BASE_URL." >&2
  echo "The requested release asset may not exist yet. Use pipx instead: pipx install mlx-manager" >&2
  exit 1
fi

if ! curl -fsL "$BASE_URL/checksums.txt" -o "$CHECKSUMS"; then
  echo "Failed to download checksums.txt from $BASE_URL." >&2
  echo "The requested release may be missing checksum assets." >&2
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
if [ "$(wc -l < "$ARCHIVE_LIST" | tr -d ' ')" != "1" ] || ! grep -qx "mlx-manager" "$ARCHIVE_LIST"; then
  echo "Unexpected archive contents in $ARTIFACT." >&2
  exit 1
fi

tar -xzf "$ARCHIVE" -C "$TMP_DIR" mlx-manager
if [ ! -f "$TMP_DIR/mlx-manager" ]; then
  echo "Archive did not contain the mlx-manager binary." >&2
  exit 1
fi
mkdir -p "$BIN_DIR"
install -m 0755 "$TMP_DIR/mlx-manager" "$BIN_DIR/mlx-manager"

case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *) echo "Note: $BIN_DIR is not on PATH. Add it before running mlx-manager." >&2 ;;
esac

echo "Installed mlx-manager to $BIN_DIR/mlx-manager"
echo "Next: mlx-manager doctor"

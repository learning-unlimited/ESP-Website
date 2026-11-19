#!/bin/bash
# Create a throwaway, INSECURE OpenPGP key pair for the check-scanning module if the
# data directory has no public key yet, so a development VM can scan and decrypt
# out of the box.  Never overwrites an existing key, and only the dev `fab` bootstrap
# runs it: production never generates a key (the real treasurer key is made offline,
# and the server must only ever hold its public half).
#
#   Usage: make_dev_treasury_key.sh [data dir]     (default /var/lib/esp-treasury)
#
# The private key has no passphrase and is left in the data directory as
# treasurer-dev-private.asc.  The module warns on its pages while that file exists.
set -euf -o pipefail

dir=${1:-/var/lib/esp-treasury}
pub=$dir/treasurer.asc
priv=$dir/treasurer-dev-private.asc
if [ -e "$pub" ]; then
    exit 0
fi
if ! command -v gpg > /dev/null; then
    echo "gpg isn't installed, so no development treasury key was created." >&2
    exit 0
fi

mkdir -p -m 700 "$dir"
work=$(mktemp -d)
cleanup() { GNUPGHOME=$work/a gpgconf --kill gpg-agent 2> /dev/null || true
            GNUPGHOME=$work/b gpgconf --kill gpg-agent 2> /dev/null || true
            rm -rf "$work"; }
trap cleanup EXIT
mkdir -m 700 "$work/a" "$work/b"
quiet=(gpg --quiet --batch --pinentry-mode loopback --passphrase '')

export GNUPGHOME=$work/a
# Keep this user ID short.  With gpg 2.4.8, a key whose user ID is 67+ characters can't be
# decrypted with after its exported private key is re-imported ("Bad secret key"); the
# self-test below catches that.  (2.4.4 doesn't have the problem.)
"${quiet[@]}" --quick-generate-key "ESP Treasury DEV INSECURE KEY <dev@example.invalid>" ed25519 cert,sign never 2> /dev/null
fpr=$(gpg --quiet --list-keys --with-colons | awk -F: '/^fpr/ {print $10; exit}' 2> /dev/null)
"${quiet[@]}" --quick-add-key "$fpr" cv25519 encr never 2> /dev/null
gpg --armor --export "$fpr" > "$work/public.asc"
(umask 077; "${quiet[@]}" --export-secret-keys --armor "$fpr" > "$work/private.asc")

# Prove the exported pair works before publishing it: encrypt to the public key, then
# decrypt in a brand-new keyring that holds only the exported private key.
echo "dev treasury key self-test" > "$work/plain.txt"
gpg --quiet --batch --trust-model always --encrypt -r "$fpr" --output "$work/plain.gpg" "$work/plain.txt" 2> /dev/null
export GNUPGHOME=$work/b
"${quiet[@]}" --import "$work/private.asc" 2> /dev/null
if [ "$("${quiet[@]}" --decrypt "$work/plain.gpg" 2> /dev/null)" != "dev treasury key self-test" ]; then
    echo "The development treasury key failed its self-test; not installing it." >&2
    exit 1
fi

(umask 077; cp "$work/private.asc" "$priv")
cp "$work/public.asc" "$pub"
cat >&2 <<EOF
*****
***** WARNING: created a development OpenPGP key pair for check scanning:
*****   $pub   (public)
*****   $priv   (PRIVATE, no passphrase)
***** The private key is on this machine, so anything scanned here is NOT
***** confidential.  Use it for testing only, never for real checks.
*****
EOF

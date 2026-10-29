#!/usr/bin/env bash
set -Eeuo pipefail

usage() {
  cat <<'EOF'
Usage:
  sudo refresh_iso.sh --iso SOURCE.iso --cwnas BINARY --root ROOT_DIR \
    [--console-unit FILE] --output OUTPUT.iso

Refresh the staged cwnas binary and frontend root in an existing CWNAS ISO.
Optionally replace the tty2 console systemd unit with an early-start unit.
The source ISO and existing output files are never overwritten.
EOF
}

die() {
  printf 'refresh_iso: %s\n' "$*" >&2
  exit 1
}

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || die "missing command: $1"
}

SOURCE_ISO=''
CWNAS_BINARY=''
FRONTEND_ROOT=''
CONSOLE_UNIT=''
OUTPUT_ISO=''

while [ "$#" -gt 0 ]; do
  case "$1" in
    --iso)
      [ "$#" -ge 2 ] || die '--iso requires a value'
      SOURCE_ISO=$2
      shift 2
      ;;
    --cwnas)
      [ "$#" -ge 2 ] || die '--cwnas requires a value'
      CWNAS_BINARY=$2
      shift 2
      ;;
    --root)
      [ "$#" -ge 2 ] || die '--root requires a value'
      FRONTEND_ROOT=$2
      shift 2
      ;;
    --console-unit)
      [ "$#" -ge 2 ] || die '--console-unit requires a value'
      CONSOLE_UNIT=$2
      shift 2
      ;;
    --output)
      [ "$#" -ge 2 ] || die '--output requires a value'
      OUTPUT_ISO=$2
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      die "unknown argument: $1"
      ;;
  esac
done

[ -n "$SOURCE_ISO" ] || die 'missing --iso'
[ -n "$CWNAS_BINARY" ] || die 'missing --cwnas'
[ -n "$FRONTEND_ROOT" ] || die 'missing --root'
[ -n "$OUTPUT_ISO" ] || die 'missing --output'
[ "${EUID:-$(id -u)}" -eq 0 ] || die 'run as root to preserve squashfs ownership and modes'

for cmd in awk chmod cmp cp cpio dd diff dirname file find grep gzip install mktemp \
  mksquashfs readlink realpath sha256sum sort stat tr unsquashfs wc xargs xorriso; do
  require_cmd "$cmd"
done

[ -f "$SOURCE_ISO" ] || die "source ISO not found: $SOURCE_ISO"
[ -f "$CWNAS_BINARY" ] || die "cwnas binary not found: $CWNAS_BINARY"
[ -x "$CWNAS_BINARY" ] || die "cwnas binary is not executable: $CWNAS_BINARY"
[ -d "$FRONTEND_ROOT" ] || die "frontend root not found: $FRONTEND_ROOT"
[ -f "$FRONTEND_ROOT/web/index.html" ] || \
  die "frontend root is incomplete: missing web/index.html"
if [ -n "$CONSOLE_UNIT" ]; then
  [ -f "$CONSOLE_UNIT" ] || die "console unit not found: $CONSOLE_UNIT"
  grep -Fxq 'After=systemd-vconsole-setup.service' "$CONSOLE_UNIT" || \
    die 'console unit must start after systemd-vconsole-setup.service'
  grep -Fxq 'TTYPath=/dev/tty2' "$CONSOLE_UNIT" || \
    die 'console unit must target /dev/tty2'
  ! grep -Eq '^(After|Wants)=.*(network-online.target|cwnas\.service)' "$CONSOLE_UNIT" || \
    die 'console unit must not wait for network-online.target or cwnas.service'
fi

SOURCE_ISO=$(readlink -f -- "$SOURCE_ISO")
CWNAS_BINARY=$(readlink -f -- "$CWNAS_BINARY")
FRONTEND_ROOT=$(readlink -f -- "$FRONTEND_ROOT")
[ -z "$CONSOLE_UNIT" ] || CONSOLE_UNIT=$(readlink -f -- "$CONSOLE_UNIT")
OUTPUT_ISO=$(realpath -m -- "$OUTPUT_ISO")
OUTPUT_DIR=$(dirname -- "$OUTPUT_ISO")
OUTPUT_NAME=$(basename -- "$OUTPUT_ISO")

[ -d "$OUTPUT_DIR" ] || die "output directory not found: $OUTPUT_DIR"
[ "$SOURCE_ISO" != "$OUTPUT_ISO" ] || die 'output ISO must differ from source ISO'
[ ! -e "$OUTPUT_ISO" ] || die "refusing to overwrite output: $OUTPUT_ISO"
[ ! -e "$OUTPUT_ISO.sha256" ] || die "refusing to overwrite checksum: $OUTPUT_ISO.sha256"
file -b -- "$CWNAS_BINARY" | grep -Eq 'ELF 64-bit.*x86-64' || \
  die 'cwnas must be an x86-64 ELF binary'

SOURCE_SHA="$SOURCE_ISO.sha256"
if [ -f "$SOURCE_SHA" ]; then
  printf '[1/9] Verify source ISO checksum\n'
  (cd "$(dirname -- "$SOURCE_ISO")" && sha256sum -c "$(basename -- "$SOURCE_SHA")")
fi

BOOT_REPORT=$(xorriso -indev "$SOURCE_ISO" -report_el_torito plain 2>&1)
SYSTEM_REPORT=$(xorriso -indev "$SOURCE_ISO" -report_system_area plain 2>&1)
grep -q 'BIOS' <<<"$BOOT_REPORT" || die 'source ISO has no BIOS El Torito entry'
grep -q 'UEFI' <<<"$BOOT_REPORT" || die 'source ISO has no UEFI El Torito entry'
grep -q 'MBR isohybrid' <<<"$SYSTEM_REPORT" || die 'source ISO is not an MBR isohybrid image'

VOLUME_ID=$(xorriso -indev "$SOURCE_ISO" -pvd_info 2>&1 | \
  awk -F': ' '/^Volume Id    : / {print $2; exit}')
[ -n "$VOLUME_ID" ] || die 'could not read source ISO volume ID'

WORK_DIR=$(mktemp -d "${TMPDIR:-/tmp}/iso-refresh.XXXXXX")
TEMP_OUTPUT=$(mktemp --tmpdir="$OUTPUT_DIR" ".${OUTPUT_NAME}.tmp.XXXXXX")
cleanup() {
  rm -rf -- "$WORK_DIR"
  rm -f -- "$TEMP_OUTPUT"
}
trap cleanup EXIT

ISO_TREE="$WORK_DIR/iso"
ROOTFS_TREE="$WORK_DIR/rootfs"
VERIFY_TREE="$WORK_DIR/verify-rootfs"
VERIFY_ISO="$WORK_DIR/verify-iso"
INITRD_TREE="$WORK_DIR/initrd"
VERIFY_INITRD_TREE="$WORK_DIR/verify-initrd"
NEW_SQUASHFS="$WORK_DIR/target-rootfs.squashfs"
NEW_INITRD="$WORK_DIR/initrd.gz"
MBR_TEMPLATE="$WORK_DIR/isohdpfx.bin"
mkdir -p \
  "$ISO_TREE" \
  "$VERIFY_ISO/cwnas" \
  "$VERIFY_ISO/install.amd/gtk" \
  "$INITRD_TREE" \
  "$VERIFY_INITRD_TREE"

printf '[2/9] Extract source ISO with xorriso\n'
xorriso -osirrox on -indev "$SOURCE_ISO" -extract / "$ISO_TREE" >/dev/null 2>&1
chmod -R u+w "$ISO_TREE"

SQUASHFS="$ISO_TREE/cwnas/target-rootfs.squashfs"
INITRD="$ISO_TREE/install.amd/gtk/initrd.gz"
[ -f "$SQUASHFS" ] || die 'source ISO lacks /cwnas/target-rootfs.squashfs'
[ -f "$INITRD" ] || die 'source ISO lacks /install.amd/gtk/initrd.gz'
[ -f "$ISO_TREE/isolinux/isolinux.bin" ] || die 'source ISO lacks BIOS boot image'
[ -f "$ISO_TREE/boot/grub/efi.img" ] || die 'source ISO lacks UEFI boot image'

printf '[3/9] Extract target squashfs\n'
unsquashfs -no-progress -d "$ROOTFS_TREE" "$SQUASHFS" >/dev/null

if [ -f "$ROOTFS_TREE/usr/lib/cwnas-installer/cwnas" ] && \
   [ -d "$ROOTFS_TREE/usr/lib/cwnas-installer/root" ]; then
  BACKEND_REL='usr/lib/cwnas-installer/cwnas'
  FRONTEND_REL='usr/lib/cwnas-installer/root'
elif [ -f "$ROOTFS_TREE/opt/cwnas/cwnas" ] && \
     [ -d "$ROOTFS_TREE/var/lib/cwnas/root" ]; then
  BACKEND_REL='opt/cwnas/cwnas'
  FRONTEND_REL='var/lib/cwnas/root'
else
  die 'target squashfs lacks a complete CWNAS payload'
fi
BACKEND_TARGET="$ROOTFS_TREE/$BACKEND_REL"
FRONTEND_TARGET="$ROOTFS_TREE/$FRONTEND_REL"
CONSOLE_TARGET="$ROOTFS_TREE/etc/systemd/system/cwnas-console.service"

printf '[4/9] Replace cwnas and frontend root\n'
install -o root -g root -m 0755 "$CWNAS_BINARY" "$BACKEND_TARGET"
rm -rf -- "$FRONTEND_TARGET"
install -d -o root -g root -m 0755 "$(dirname -- "$FRONTEND_TARGET")"
cp -a -- "$FRONTEND_ROOT" "$FRONTEND_TARGET"
chown -R root:root "$FRONTEND_TARGET"
if [ -n "$CONSOLE_UNIT" ]; then
  [ -f "$CONSOLE_TARGET" ] || \
    die 'target squashfs lacks /etc/systemd/system/cwnas-console.service'
  install -o root -g root -m 0644 "$CONSOLE_UNIT" "$CONSOLE_TARGET"
fi

printf '[5/9] Rebuild target squashfs and synchronize media identity\n'
mksquashfs "$ROOTFS_TREE" "$NEW_SQUASHFS" -noappend -comp xz -b 1M -no-progress >/dev/null
install -m 0644 "$NEW_SQUASHFS" "$SQUASHFS"
ROOTFS_HASH=$(sha256sum "$SQUASHFS" | awk '{print $1}')
printf '%s  target-rootfs.squashfs\n' "$ROOTFS_HASH" \
  >"$ISO_TREE/cwnas/target-rootfs.squashfs.sha256"
printf '%s\n' "$ROOTFS_HASH" >"$ISO_TREE/cwnas/MEDIA_ID"

gzip -dc "$INITRD" | (cd "$INITRD_TREE" && cpio -idm --quiet)
[ -x "$INITRD_TREE/init" ] || die 'source initrd is incomplete: missing executable /init'
[ -f "$INITRD_TREE/etc/cwnas-media-id" ] || \
  die 'source initrd lacks /etc/cwnas-media-id'
printf '%s\n' "$ROOTFS_HASH" >"$INITRD_TREE/etc/cwnas-media-id"
(
  cd "$INITRD_TREE"
  find . -print0 | cpio --null -ov --format=newc 2>/dev/null | gzip -9 >"$NEW_INITRD"
)
install -m 0644 "$NEW_INITRD" "$INITRD"

(
  cd "$ISO_TREE"
  find . -type f ! -name 'boot.cat' ! -name 'sha256sum.txt' \
    ! -path './isolinux/isolinux.bin' ! -path './.disk/*' -print0 | \
    sort -z | xargs -0 sha256sum >sha256sum.txt
)

dd if="$SOURCE_ISO" of="$MBR_TEMPLATE" bs=1 count=432 status=none

printf '[6/9] Repack BIOS/UEFI hybrid ISO\n'
xorriso -as mkisofs \
  -r -J -joliet-long \
  -V "$VOLUME_ID" \
  -o "$TEMP_OUTPUT" \
  -isohybrid-mbr "$MBR_TEMPLATE" \
  -b isolinux/isolinux.bin -c isolinux/boot.cat \
  -boot-load-size 4 -boot-info-table -no-emul-boot \
  -eltorito-alt-boot -e boot/grub/efi.img -no-emul-boot \
  -isohybrid-gpt-basdat \
  "$ISO_TREE" >/dev/null
mv -- "$TEMP_OUTPUT" "$OUTPUT_ISO"
chmod 0644 "$OUTPUT_ISO"
(
  cd "$OUTPUT_DIR"
  sha256sum "$OUTPUT_NAME" >"$OUTPUT_NAME.sha256"
  sha256sum -c "$OUTPUT_NAME.sha256"
)

printf '[7/9] Verify embedded payloads and nested checksums\n'
xorriso -osirrox on -indev "$OUTPUT_ISO" \
  -extract /cwnas/target-rootfs.squashfs "$VERIFY_ISO/cwnas/target-rootfs.squashfs" \
  -extract /cwnas/target-rootfs.squashfs.sha256 "$VERIFY_ISO/cwnas/target-rootfs.squashfs.sha256" \
  -extract /cwnas/MEDIA_ID "$VERIFY_ISO/cwnas/MEDIA_ID" \
  -extract /install.amd/gtk/initrd.gz "$VERIFY_ISO/install.amd/gtk/initrd.gz" \
  -extract /sha256sum.txt "$VERIFY_ISO/sha256sum.txt" >/dev/null 2>&1
(
  cd "$VERIFY_ISO/cwnas"
  sha256sum -c target-rootfs.squashfs.sha256
)
VERIFIED_HASH=$(sha256sum "$VERIFY_ISO/cwnas/target-rootfs.squashfs" | awk '{print $1}')
[ "$(tr -d '\r\n' <"$VERIFY_ISO/cwnas/MEDIA_ID")" = "$VERIFIED_HASH" ] || \
  die 'embedded MEDIA_ID does not match target squashfs'
awk '$2 == "./cwnas/target-rootfs.squashfs" || \
     $2 == "./cwnas/target-rootfs.squashfs.sha256" || \
     $2 == "./cwnas/MEDIA_ID" || \
     $2 == "./install.amd/gtk/initrd.gz"' "$VERIFY_ISO/sha256sum.txt" \
  >"$VERIFY_ISO/sha256sum.subset.txt"
[ "$(wc -l <"$VERIFY_ISO/sha256sum.subset.txt")" -eq 4 ] || \
  die 'ISO sha256sum.txt lacks refreshed CWNAS entries'
(cd "$VERIFY_ISO" && sha256sum -c sha256sum.subset.txt)

unsquashfs -no-progress -d "$VERIFY_TREE" \
  "$VERIFY_ISO/cwnas/target-rootfs.squashfs" >/dev/null
cmp -- "$CWNAS_BINARY" "$VERIFY_TREE/$BACKEND_REL"
[ "$(stat -c '%a' "$VERIFY_TREE/$BACKEND_REL")" = '755' ] || \
  die 'embedded cwnas mode is not 0755'
diff -qr --no-dereference "$FRONTEND_ROOT" "$VERIFY_TREE/$FRONTEND_REL"
if [ -n "$CONSOLE_UNIT" ]; then
  cmp -- "$CONSOLE_UNIT" \
    "$VERIFY_TREE/etc/systemd/system/cwnas-console.service"
  [ "$(stat -c '%a' "$VERIFY_TREE/etc/systemd/system/cwnas-console.service")" = '644' ] || \
    die 'embedded console unit mode is not 0644'
fi

printf '[8/9] Verify initrd media identity\n'
gzip -dc "$VERIFY_ISO/install.amd/gtk/initrd.gz" | \
  (cd "$VERIFY_INITRD_TREE" && cpio -idm --quiet etc/cwnas-media-id)
[ -f "$VERIFY_INITRD_TREE/etc/cwnas-media-id" ] || \
  die 'output initrd lacks /etc/cwnas-media-id'
[ "$(tr -d '\r\n' <"$VERIFY_INITRD_TREE/etc/cwnas-media-id")" = "$VERIFIED_HASH" ] || \
  die 'output initrd media identity does not match target squashfs'

printf '[9/9] Verify final BIOS/UEFI boot records\n'
FINAL_BOOT_REPORT=$(xorriso -indev "$OUTPUT_ISO" -report_el_torito plain 2>&1)
FINAL_SYSTEM_REPORT=$(xorriso -indev "$OUTPUT_ISO" -report_system_area plain 2>&1)
grep -q 'BIOS' <<<"$FINAL_BOOT_REPORT" || die 'output ISO has no BIOS El Torito entry'
grep -q 'UEFI' <<<"$FINAL_BOOT_REPORT" || die 'output ISO has no UEFI El Torito entry'
grep -q 'MBR isohybrid' <<<"$FINAL_SYSTEM_REPORT" || die 'output ISO is not MBR isohybrid'

printf 'ISO: %s\n' "$OUTPUT_ISO"
printf 'SHA256: %s\n' "$(sha256sum "$OUTPUT_ISO" | awk '{print $1}')"
printf 'Artifact verification complete; runtime boot/install was not tested.\n'

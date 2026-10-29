#!/usr/bin/env bash

set -euo pipefail

repo="/home/skynit/workspace/cwnas_client"
platform_host="filesharing.asia"
application_id="com.cwnas.client.android"

usage() {
  printf 'Usage: %s [--repo DIR] [--host HOST]\n' "$0"
}

fail() {
  printf 'ERROR: %s\n' "$*" >&2
  exit 1
}

require_command() {
  command -v "$1" >/dev/null 2>&1 || fail "Required command not found: $1"
}

while (($# > 0)); do
  case "$1" in
    --repo)
      (($# >= 2)) || fail "--repo requires a directory"
      repo="$2"
      shift 2
      ;;
    --host)
      (($# >= 2)) || fail "--host requires a platform authority"
      platform_host="$2"
      shift 2
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "Unknown argument: $1"
      ;;
  esac
done

[[ "$platform_host" =~ ^[A-Za-z0-9.-]+(:[0-9]+)?$ ]] ||
  fail "--host must be an authority without scheme or path"
[[ -d "$repo/.git" ]] || fail "Not a Git repository: $repo"
[[ -f "$repo/pubspec.yaml" ]] || fail "Flutter project not found: $repo"
[[ -f "$repo/lib/mobile_main.dart" ]] || fail "Mobile entrypoint not found: $repo/lib/mobile_main.dart"

for command_name in flutter git rustup unzip strings sha256sum cmp find sort sed grep cp \
  dirname date mv mkdir stat cut diff head mktemp rm; do
  require_command "$command_name"
done

work_dir="$(mktemp -d)"
trap 'rm -rf -- "$work_dir"' EXIT

before_status="$work_dir/git-status-before"
after_status="$work_dir/git-status-after"
badging_file="$work_dir/badging.txt"
signing_file="$work_dir/signing.txt"
native_lib="$work_dir/libapp.so"

git -C "$repo" status --porcelain=v1 >"$before_status"

stable_rustc="$(rustup which --toolchain stable rustc)"
stable_cargo="$(rustup which --toolchain stable cargo)"
required_targets=(
  armv7-linux-androideabi
  aarch64-linux-android
  x86_64-linux-android
)
installed_targets="$(rustup target list --installed --toolchain stable)"

for target in "${required_targets[@]}"; do
  if ! grep -Fxq "$target" <<<"$installed_targets"; then
    printf 'Installing Rust target %s for stable...\n' "$target"
    rustup target add --toolchain stable "$target"
  fi
done

stale_cache_found=false
if [[ -d "$repo/build" ]]; then
  while IFS= read -r rust_info; do
    if grep -Fq '\n/usr\n' "$rust_info"; then
      cache_dir="$(dirname "$rust_info")"
      backup_dir="${cache_dir}.stale-system-rustc-$(date +%Y%m%d%H%M%S)"
      printf 'Isolating stale Cargokit cache: %s -> %s\n' "$cache_dir" "$backup_dir"
      mv -- "$cache_dir" "$backup_dir"
      stale_cache_found=true
    fi
  done < <(
    find "$repo/build" -mindepth 2 -maxdepth 3 \
      -type d -name '*.stale-system-rustc-*' -prune -o \
      -type f -name .rustc_info.json -print
  )
fi

if [[ "$stale_cache_found" == true && -x "$repo/android/gradlew" ]]; then
  (cd "$repo/android" && ./gradlew --stop)
fi

printf 'Building CWNAS Android APK for %s...\n' "$platform_host"
(
  cd "$repo"
  RUSTUP_TOOLCHAIN=stable \
    RUSTC="$stable_rustc" \
    CARGO="$stable_cargo" \
    flutter build apk \
      --release \
      --target lib/mobile_main.dart \
      --dart-define="CW_PLATFORM_WEB_HOST=$platform_host"
)

source_apk="$repo/build/app/outputs/flutter-apk/app-release.apk"
[[ -s "$source_apk" ]] || fail "Flutter did not produce a non-empty APK: $source_apk"

android_sdk="${ANDROID_SDK_ROOT:-${ANDROID_HOME:-}}"
if [[ -z "$android_sdk" && -f "$repo/android/local.properties" ]]; then
  android_sdk="$(sed -n '/^sdk\.dir=/{s/^sdk\.dir=//;p;q;}' "$repo/android/local.properties")"
fi
[[ -d "$android_sdk/build-tools" ]] || fail "Android SDK build-tools not found"

build_tools_version="$(find "$android_sdk/build-tools" -mindepth 1 -maxdepth 1 -type d -printf '%f\n' | sort -V | tail -n 1)"
build_tools="$android_sdk/build-tools/$build_tools_version"
for android_tool in aapt apksigner zipalign; do
  [[ -x "$build_tools/$android_tool" ]] || fail "Android tool not found: $build_tools/$android_tool"
done

"$build_tools/aapt" dump badging "$source_apk" >"$badging_file"
package_line="$(grep -m1 '^package:' "$badging_file")"
[[ "$package_line" == *"name='$application_id'"* ]] || fail "Unexpected application ID"
[[ "$package_line" =~ versionName=\'([^\']+)\' ]] || fail "Unable to read APK versionName"
version_name="${BASH_REMATCH[1]}"
[[ "$package_line" =~ versionCode=\'([^\']+)\' ]] || fail "Unable to read APK versionCode"
version_code="${BASH_REMATCH[1]}"

grep -Fq "uses-permission: name='android.permission.CAMERA'" "$badging_file" ||
  fail "APK does not declare android.permission.CAMERA"

native_code_line="$(grep -m1 '^native-code:' "$badging_file")"
for abi in arm64-v8a armeabi-v7a x86_64; do
  [[ "$native_code_line" == *"'$abi'"* ]] || fail "APK is missing ABI: $abi"
done

"$build_tools/apksigner" verify --verbose --print-certs "$source_apk" >"$signing_file"
"$build_tools/zipalign" -c -P 16 4 "$source_apk"

unzip -p "$source_apk" lib/arm64-v8a/libapp.so >"$native_lib"
if ! strings "$native_lib" | grep -F "$platform_host" >/dev/null; then
  fail "Platform host is not embedded in the Android application"
fi

release_dir="$repo/build/releases"
mkdir -p "$release_dir"
host_tag="${platform_host//./_}"
host_tag="${host_tag//:/_}"
release_apk="$release_dir/cwnas_client_android_v${version_name}_${host_tag}_scan.apk"
cp --preserve=timestamps "$source_apk" "$release_apk"
cmp "$source_apk" "$release_apk"

git -C "$repo" status --porcelain=v1 >"$after_status"
if ! cmp -s "$before_status" "$after_status"; then
  printf 'Git status changed during the build:\n' >&2
  diff -u "$before_status" "$after_status" >&2 || true
  fail "Build changed the source worktree; files were not reverted"
fi

apk_size="$(stat --printf='%s' "$release_apk")"
apk_sha256="$(sha256sum "$release_apk" | cut -d' ' -f1)"
signer="$(grep -m1 '^Signer #1 certificate DN:' "$signing_file" | sed 's/^Signer #1 certificate DN: //')"

printf '\nAPK=%s\n' "$release_apk"
printf 'APPLICATION_ID=%s\n' "$application_id"
printf 'VERSION_NAME=%s\n' "$version_name"
printf 'VERSION_CODE=%s\n' "$version_code"
printf 'PLATFORM_HOST=%s\n' "$platform_host"
printf 'BYTES=%s\n' "$apk_size"
printf 'SHA256=%s\n' "$apk_sha256"
printf 'SIGNER=%s\n' "$signer"
printf 'ABIS=arm64-v8a,armeabi-v7a,x86_64\n'
printf 'CAMERA_PERMISSION=verified\n'
printf 'APK_SIGNATURE=verified\n'
printf 'ZIPALIGN=verified\n'
printf 'SOURCE_STATUS=unchanged\n'

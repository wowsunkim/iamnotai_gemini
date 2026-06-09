#!/bin/bash
# im-not-ai DMG 빌드 스크립트
set -e

APP_NAME="im-not-ai"
VERSION="1.0"
APP_PATH="dist/${APP_NAME}.app"
DMG_OUT="dist/${APP_NAME}-${VERSION}.dmg"
TMP_DMG="dist/tmp_rw.dmg"
VOL_NAME="${APP_NAME}"
STAGING="dist/dmg_staging"

echo "▶ DMG 빌드 시작"

# 1. 정리
rm -rf "${STAGING}" "${TMP_DMG}" "${DMG_OUT}"
mkdir -p "${STAGING}"

# 2. 앱 + Applications 심링크
echo "  → 스테이징 준비..."
cp -R "${APP_PATH}" "${STAGING}/"
ln -s /Applications "${STAGING}/Applications"

# 3. 읽기/쓰기 임시 DMG 생성
SIZE_KB=$(du -sk "${STAGING}" | awk '{print $1}')
SIZE_MB=$(( (SIZE_KB / 1024) + 15 ))
echo "  → 임시 DMG 생성 (${SIZE_MB}MB)..."
hdiutil create \
    -srcfolder "${STAGING}" \
    -volname "${VOL_NAME}" \
    -fs HFS+ \
    -format UDRW \
    -size "${SIZE_MB}m" \
    "${TMP_DMG}" > /dev/null

# 4. 마운트
echo "  → 마운트..."
DEV=$(hdiutil attach -readwrite -noverify -noautoopen "${TMP_DMG}" \
    | grep "^/dev" | head -1 | awk '{print $1}')
MOUNT="/Volumes/${VOL_NAME}"
sleep 2
echo "     장치: ${DEV}  경로: ${MOUNT}"

# 5. Finder 창 배치 (실패해도 계속)
osascript - "${MOUNT}" "${APP_NAME}" <<'APPLESCRIPT' || true
on run argv
    set mountPath to item 1 of argv
    set appName to item 2 of argv
    tell application "Finder"
        tell disk appName
            open
            set current view of container window to icon view
            set toolbar visible of container window to false
            set statusbar visible of container window to false
            set bounds of container window to {400, 100, 900, 400}
            set icon size of (icon view options of container window) to 96
            set position of item (appName & ".app") of container window to {140, 150}
            set position of item "Applications" of container window to {360, 150}
            close
            open
            update without registering applications
            delay 1
            close
        end tell
    end tell
end run
APPLESCRIPT

# 6. 언마운트
sync; sleep 1
hdiutil detach "${DEV}" -quiet
echo "  → 언마운트 완료"

# 7. 압축 변환
echo "  → 압축 DMG 변환..."
hdiutil convert "${TMP_DMG}" \
    -format UDZO \
    -imagekey zlib-level=9 \
    -o "${DMG_OUT}" > /dev/null

# 8. 임시 파일 삭제
rm -rf "${STAGING}" "${TMP_DMG}"

SIZE=$(du -sh "${DMG_OUT}" | awk '{print $1}')
echo ""
echo "✅ 완료!"
echo "   ${DMG_OUT}  (${SIZE})"

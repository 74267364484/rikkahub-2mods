#!/usr/bin/env bash
# 一键重建(需要: JDK 17+, python3, baksmali/smali/dexlib2/util/guava/jcommander/antlr/apksig 等 jar 放同目录)
set -e
APK="${1:-/workspace/RikkaHub_2.5.6.apk}"
WORK="${2:-/workspace/apkwork}"
CP="baksmali.jar:dexlib2.jar:util.jar:guava.jar:jcommander.jar:antlr.jar"
SCP="smali.jar:dexlib2.jar:util.jar:guava.jar:jcommander.jar:antlr.jar"
mkdir -p "$WORK/dex"; cd "$WORK"
python3 - <<PY
import zipfile
z=zipfile.ZipFile("$APK")
for n in ['classes.dex','classes2.dex','classes3.dex']:
    open('dex/'+n,'wb').write(z.read(n))
PY
for i in 1 2 3; do
  d=smali$i; [ $i -eq 1 ] && d=smali1
  java -cp "$CP" org.jf.baksmali.Main d dex/classes$([ $i -eq 1 ] && echo "" || echo $i).dex -o $d
done
python3 patch/patch_smali.py
for i in 1 2 3; do
  java -cp "$SCP" org.jf.smali.Main a smali$i -o out$i.dex -a 26
done
python3 patch/patch_axml.py "$APK" AndroidManifest_new.xml --label "RikkaHub Mod"
python3 patch/build_apk.py
javac -cp apksig.jar patch/Sign.java -d .
java -cp "apksig.jar:." Sign rikkahub-mod.keystore <你的keystore密码> rikkahub RikkaHub_2.5.6-mod-unsigned.apk RikkaHub_2.5.6-mod.apk
echo "完成: $WORK/RikkaHub_2.5.6-mod.apk"

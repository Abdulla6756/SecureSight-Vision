# طريقة بناء SecureSight Vision كملف EXE على Windows

## الملفات المطلوبة

أهم ملف عندك هو:

```bat
BUILD_WINDOWS_EXE_CPU.bat
```

هذا الملف يبني نسخة EXE تعمل على CPU وتستخدم parallelization قدر الإمكان.

## المتطلبات على جهاز Windows

- Windows 10 أو Windows 11
- Python 3.11
- إنترنت أول مرة حتى يثبت المكتبات

لا تحتاج Node.js بعد بناء الـ EXE، لأن الواجهة تنخدم من داخل FastAPI.

## خطوات البناء

1. فك ضغط المشروع.
2. افتح المجلد.
3. شغل:

```bat
BUILD_WINDOWS_EXE_CPU.bat
```

4. انتظر لين يخلص.
5. راح تلقى الناتج هنا:

```text
dist\SecureSightVision\SecureSightVision.exe
```

## مهم للتسليم

لا تسلم ملف `SecureSightVision.exe` لوحده.

سلّم أو اضغط كامل المجلد:

```text
dist\SecureSightVision\
```

لأن مكتبات Python وملفات التشغيل تكون بجانب ملف الـ EXE.

## تشغيل البرنامج بعد البناء

افتح:

```text
dist\SecureSightVision\SecureSightVision.exe
```

راح يفتح المتصفح تلقائياً.

## ملاحظات عن parallel على CPU

النسخة تستخدم:

```text
FACE_PROVIDER=cpu
FACE_CPU_WORKERS=auto
```

يعني:

- التعرف يعمل على CPU.
- يحاول يحلل الفريمات بالتوازي بشكل آمن.
- حفظ صور unknown faces يعمل بالتوازي.
- منطق التقرير، entry/exit، و unknown deduplication يبقى مرتب حسب وقت الفيديو حتى ما يخرب التقرير.

إذا الجهاز ضعيف وعلّق أو صار بطيء، شغل من Command Prompt بهذه الطريقة:

```bat
set FACE_CPU_WORKERS=1
SecureSightVision.exe
```

أو جرّب:

```bat
set FACE_CPU_WORKERS=2
SecureSightVision.exe
```

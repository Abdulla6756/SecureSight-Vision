# إصلاح خطأ SciPy في نسخة CPU EXE

إذا ظهر الخطأ:

```text
Face recognition engine is not ready. Details: The `scipy` install you are using seems to be broken
```

فالسبب غالباً أن بيئة البناء القديمة `.build_venv` أو ملفات PyInstaller القديمة جمعت SciPy ناقصة أو بإصدار غير متوافق.

## الحل السريع

1. اقفل البرنامج.
2. من مجلد المشروع احذف هذه المجلدات إن وجدت:

```text
.build_venv
build
dist
```

3. شغل:

```bat
BUILD_WINDOWS_EXE_CPU.bat
```

4. بعد البناء شغل:

```text
dist\SecureSightVision\SecureSightVision.exe
```

## ماذا تغير في هذه النسخة؟

- تم تثبيت `scipy==1.11.4` بشكل صريح.
- تم تثبيت `numpy==1.26.4` بشكل صريح.
- تم تثبيت `scikit-image` و `scikit-learn` بإصدارات ثابتة.
- تم إضافة preflight قبل بناء EXE يفحص أن SciPy وامتداداته تعمل.
- تم تحديث PyInstaller spec ليجمع SciPy وملفاتها الثنائية.
- تم إيقاف UPX في PyInstaller لتجنب ضغط/إتلاف ملفات DLL أو PYD الخاصة بالمكتبات العلمية.

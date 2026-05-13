# إصلاح خطأ No module named matplotlib

إذا ظهر أثناء تحليل الفيديو داخل نسخة الـ EXE:

```text
Face recognition engine is not ready. Details: No module named 'matplotlib'
```

فالسبب أن `insightface` يستورد `matplotlib` داخلياً حتى لو SecureSight Vision لا يستخدم الرسومات مباشرة.

تم إصلاحه في هذه النسخة عبر:

- إضافة `matplotlib==3.8.4` إلى `backend/cpu_requirements.txt`.
- تعديل `SecureSightVision.spec` لتجميع `matplotlib` لكن بدون test suites.
- فرض backend غير رسومي داخل EXE:

```text
MPLBACKEND=Agg
```

هذا يمنع الحاجة إلى نوافذ Tkinter أثناء التشغيل.

## بعد التحديث

إذا بنيت نسخة قديمة سابقاً، احذف من مجلد المشروع:

```text
.build_venv
build
dist
```

ثم شغل:

```bat
BUILD_WINDOWS_EXE_CPU.bat
```

# إصلاح خطأ PyInstaller مع onnx.reference

إذا ظهر الخطأ:

```text
Isolated subprocess crashed while importing package 'onnx.reference'
```

فهذا لا يعني أن مشروع SecureSight Vision فشل في التشغيل. المشكلة أن PyInstaller كان يجمع حزم اختبارية وأدوات تطوير غير مطلوبة مثل:

- `onnx.reference`
- `onnxruntime.tools`
- `onnxruntime.transformers`
- `sklearn.*.tests`
- `scipy.*.tests`
- `matplotlib`
- `tkinter`

هذه الحزم ليست مطلوبة لتشغيل تحليل الفيديو أو التعرف على الوجوه، لكنها كانت تدخل في ملف EXE بسبب `collect_all` داخل ملف `.spec`.

## ماذا تغير؟

تم تعديل `SecureSightVision.spec` ليستخدم تجميع أخف:

- يجمع ملفات الواجهة والبيانات.
- يجمع DLLs المهمة من `onnxruntime`, `cv2`, `numpy`, `scipy`.
- يجمع runtime submodules الخاصة بـ `insightface` فقط.
- يستبعد أدوات ONNX/ONNXRuntime الاختبارية والتطويرية.
- يستبعد test suites الثقيلة من sklearn/scipy/numpy/skimage.

## طريقة البناء

من مجلد المشروع شغل:

```bat
BUILD_WINDOWS_EXE_CPU.bat
```

إذا كنت قد حاولت البناء من قبل، احذف هذه المجلدات إن وجدت ثم أعد التشغيل:

```text
.build_venv
build
dist
```

الناتج سيكون في:

```text
dist\SecureSightVision\SecureSightVision.exe
```

للتسليم، سلّم كامل مجلد:

```text
dist\SecureSightVision\
```

## ملاحظة matplotlib

لا يتم حذف `matplotlib` بالكامل لأن `insightface` قد يحتاجه عند الاستيراد. يتم تجميعه بوضع `Agg` فقط وبدون ملفات tests أو backends الرسومية الثقيلة.

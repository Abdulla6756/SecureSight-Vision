# حل خطأ ONNXRuntime DLL في نسخة CPU EXE

إذا ظهر الخطأ:

```text
DLL load failed while importing onnxruntime_pybind11_state:
A dynamic link library (DLL) initialization routine failed.
```

فهذا يعني أن مكتبة ONNXRuntime CPU لم تشتغل داخل بيئة البناء. غالباً السبب واحد من التالي:

1. بيئة `.build_venv` قديمة أو فيها onnxruntime-gpu متبقي.
2. Microsoft Visual C++ Runtime غير مثبت على Windows.
3. نسخة ONNXRuntime الحالية لا تعمل على الجهاز.
4. الجهاز قديم جداً ولا يدعم تعليمات AVX المطلوبة من ONNXRuntime.

## الحل في هذه النسخة

ملف البناء الجديد:

```bat
BUILD_WINDOWS_EXE_CPU.bat
```

يسوي التالي تلقائياً:

- يعيد إنشاء `.build_venv` إذا كانت من إصدار قديم.
- يحذف `onnxruntime-gpu` و `onnxruntime` قبل التثبيت.
- يثبت نسخة CPU فقط.
- يجرب أكثر من نسخة ONNXRuntime CPU:
  - `1.18.1`
  - `1.17.3`
  - `1.16.3`
- يفحص import قبل بناء EXE.

## إذا بقي الخطأ

ثبت هذا من مايكروسوفت:

**Microsoft Visual C++ Redistributable 2015-2022 x64**

ثم احذف هذه المجلدات:

```text
.build_venv
build
dist
```

وشغل:

```bat
BUILD_WINDOWS_EXE_CPU.bat
```

## ملاحظة مهمة

إذا كان المعالج قديم جداً ولا يدعم AVX، قد لا تعمل ONNXRuntime CPU عليه حتى لو كان كل شيء مثبت بشكل صحيح. في هذه الحالة يلزم جهاز أحدث أو تشغيل المشروع من Python عادي مع نسخة ORT مناسبة إن توفرت.

"""NVIDIA Maxine AR SDK GazeRedirection - ctypes wrapper (Variant A).

nvARPose.dll / NVCVImage.dll to'g'ridan yuklanadi, C++ build kerak emas.
Har kadr: CPU BGR -> GPU -> NvAR_Run -> GPU -> CPU BGR + gaze/head/landmark chiqishlari.
"""
import ctypes as C
import math
import os

import numpy as np

_PORTABLE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "runtime", "maxine")
_SYSTEM = r"C:\Program Files\NVIDIA Corporation\NVIDIA AR SDK"
# Tartib: NVAR_SDK_DIR muhit o'zgaruvchisi -> paket ichidagi runtime/maxine (portativ, o'rnatish kerak emas) -> tizim
SDK_DIR = os.environ.get("NVAR_SDK_DIR") or (_PORTABLE if os.path.exists(os.path.join(_PORTABLE, "nvARPose.dll")) else _SYSTEM)
MODEL_DIR = os.path.join(SDK_DIR, "models")

NVCV_BGR, NVCV_U8, NVCV_CHUNKY, NVCV_CPU, NVCV_GPU = 5, 1, 0, 0, 1


class NvCVImage(C.Structure):
    _fields_ = [
        ("width", C.c_uint), ("height", C.c_uint), ("pitch", C.c_int),
        ("pixelFormat", C.c_int), ("componentType", C.c_int),
        ("pixelBytes", C.c_ubyte), ("componentBytes", C.c_ubyte), ("numComponents", C.c_ubyte),
        ("planar", C.c_ubyte), ("gpuMem", C.c_ubyte), ("colorspace", C.c_ubyte), ("reserved", C.c_ubyte * 2),
        ("pixels", C.c_void_p), ("deletePtr", C.c_void_p), ("deleteProc", C.c_void_p),
        ("bufferBytes", C.c_ulonglong),
    ]


assert C.sizeof(NvCVImage) == 64, C.sizeof(NvCVImage)


class Point2f(C.Structure):
    _fields_ = [("x", C.c_float), ("y", C.c_float)]


class Point3f(C.Structure):
    _fields_ = [("x", C.c_float), ("y", C.c_float), ("z", C.c_float)]


class Quaternion(C.Structure):
    _fields_ = [("x", C.c_float), ("y", C.c_float), ("z", C.c_float), ("w", C.c_float)]


class Rect(C.Structure):
    _fields_ = [("x", C.c_float), ("y", C.c_float), ("width", C.c_float), ("height", C.c_float)]


class BBoxes(C.Structure):
    _fields_ = [("boxes", C.POINTER(Rect)), ("num_boxes", C.c_ubyte), ("max_boxes", C.c_ubyte)]


def _cfg(n):
    return f"NvAR_Parameter_Config_{n}".encode()


def _inp(n):
    return f"NvAR_Parameter_Input_{n}".encode()


def _out(n):
    return f"NvAR_Parameter_Output_{n}".encode()


class NvARError(RuntimeError):
    pass


def _chk(status, what):
    if status != 0:
        raise NvARError(f"{what}: NvCV status {status}")


def quat_to_euler_deg(q):
    """Kvaternion -> (yaw, pitch, roll) gradusda."""
    x, y, z, w = q.x, q.y, q.z, q.w
    sinp = 2 * (w * y - z * x)
    pitch = math.degrees(math.asin(max(-1.0, min(1.0, sinp))))
    yaw = math.degrees(math.atan2(2 * (w * z + x * y), 1 - 2 * (y * y + z * z)))
    roll = math.degrees(math.atan2(2 * (w * x + y * z), 1 - 2 * (x * x + y * y)))
    return yaw, pitch, roll


class GazeRedirector:
    def __init__(self, width, height, *, temporal=True, eye_size_sensitivity=3, landmarks=68,
                 use_cuda_graph=True, gaze_thr=(20.0, 30.0), head_pitch_thr=(15.0, 25.0),
                 head_yaw_thr=(25.0, 30.0), model_dir=None, redirect=True, sdk_dir=None):
        """redirect=False: faqat estimator (landmark, gaze, head pose), chiqish rasm yo'q."""
        self.w, self.h, self.redirect = width, height, redirect
        sdk_dir = sdk_dir or SDK_DIR
        model_dir = model_dir or os.path.join(sdk_dir, "models")
        os.add_dll_directory(sdk_dir)
        ar = self.ar = C.CDLL(os.path.join(sdk_dir, "nvARPose.dll"))
        cv = self.cv = C.CDLL(os.path.join(sdk_dir, "NVCVImage.dll"))
        ar.NvAR_SetF32.argtypes = [C.c_void_p, C.c_char_p, C.c_float]
        ar.NvAR_SetObject.argtypes = [C.c_void_p, C.c_char_p, C.c_void_p, C.c_ulong]
        ar.NvAR_SetF32Array.argtypes = [C.c_void_p, C.c_char_p, C.c_void_p, C.c_int]
        cv.NvCVImage_Transfer.argtypes = [C.c_void_p, C.c_void_p, C.c_float, C.c_void_p, C.c_void_p]
        cv.NvCVImage_Init.argtypes = [C.c_void_p, C.c_uint, C.c_uint, C.c_int, C.c_void_p,
                                      C.c_int, C.c_int, C.c_uint, C.c_uint]
        cv.NvCVImage_Alloc.argtypes = [C.c_void_p, C.c_uint, C.c_uint, C.c_int, C.c_int,
                                       C.c_uint, C.c_uint, C.c_uint]

        self.stream = C.c_void_p()
        _chk(ar.NvAR_CudaStreamCreate(C.byref(self.stream)), "CudaStreamCreate")
        self.hnd = C.c_void_p()
        _chk(ar.NvAR_Create(b"GazeRedirection", C.byref(self.hnd)), "Create")
        h = self.hnd
        _chk(ar.NvAR_SetString(h, _cfg("ModelDir"), model_dir.encode()), "ModelDir")
        _chk(ar.NvAR_SetU32(h, _cfg("Landmarks_Size"), landmarks), "Landmarks_Size")
        _chk(ar.NvAR_SetU32(h, _cfg("Temporal"), 0xFFFFFFFF if temporal else 0), "Temporal")
        _chk(ar.NvAR_SetU32(h, _cfg("GazeRedirect"), 1 if redirect else 0), "GazeRedirect")
        _chk(ar.NvAR_SetU32(h, _cfg("EnableLookAway"), 0), "EnableLookAway")
        _chk(ar.NvAR_SetU32(h, _cfg("UseCudaGraph"), 1 if use_cuda_graph else 0), "UseCudaGraph")
        _chk(ar.NvAR_SetU32(h, _cfg("EyeSizeSensitivity"), eye_size_sensitivity), "EyeSizeSensitivity")
        for name, (lo, hi) in (("GazePitch", gaze_thr), ("GazeYaw", gaze_thr),
                               ("HeadPitch", head_pitch_thr), ("HeadYaw", head_yaw_thr)):
            _chk(ar.NvAR_SetF32(h, _cfg(f"{name}ThresholdLow"), lo), name)
            _chk(ar.NvAR_SetF32(h, _cfg(f"{name}ThresholdHigh"), hi), name)
        _chk(ar.NvAR_SetCudaStream(h, _cfg("CUDAStream"), self.stream), "CUDAStream")
        _chk(ar.NvAR_Load(h), "Load (model yuklash)")

        self.gpu_in, self.gpu_out, self.tmp = NvCVImage(), NvCVImage(), NvCVImage()
        self.cpu_in, self.cpu_out = NvCVImage(), NvCVImage()
        for im in ((self.gpu_in, self.gpu_out) if redirect else (self.gpu_in,)):
            _chk(cv.NvCVImage_Alloc(C.byref(im), width, height, NVCV_BGR, NVCV_U8, NVCV_CHUNKY, NVCV_GPU, 1), "Alloc")
        _chk(ar.NvAR_SetObject(h, _inp("Image"), C.byref(self.gpu_in), C.sizeof(NvCVImage)), "Input_Image")
        if redirect:
            _chk(ar.NvAR_SetObject(h, _out("Image"), C.byref(self.gpu_out), C.sizeof(NvCVImage)), "Output_Image")
        _chk(ar.NvAR_SetS32(h, _inp("Width"), width), "Width")
        _chk(ar.NvAR_SetS32(h, _inp("Height"), height), "Height")

        n = C.c_uint()
        _chk(ar.NvAR_GetU32(h, _cfg("Landmarks_Size"), C.byref(n)), "GetLandmarks_Size")
        self.n_lm = n.value
        self.landmarks = (Point2f * self.n_lm)()
        self.gaze_landmarks = (Point2f * (12 if self.n_lm == 68 else 24))()
        self.conf = (C.c_float * self.n_lm)()
        self.gaze = (C.c_float * 2)()
        self.head_t = (C.c_float * 3)()
        self.head_pose = Quaternion()
        self.gaze_dir = (Point3f * 2)()
        self.rect = Rect()
        self.bboxes = BBoxes(C.pointer(self.rect), 1, 1)
        _chk(ar.NvAR_SetObject(h, _out("Landmarks"), self.landmarks, C.sizeof(Point2f)), "Landmarks")
        _chk(ar.NvAR_SetObject(h, _out("GazeOutputLandmarks"), self.gaze_landmarks, C.sizeof(Point2f)),
             "GazeOutputLandmarks")
        _chk(ar.NvAR_SetF32Array(h, _out("LandmarksConfidence"), self.conf, self.n_lm), "LandmarksConfidence")
        _chk(ar.NvAR_SetF32Array(h, _out("OutputGazeVector"), self.gaze, 2), "OutputGazeVector")
        _chk(ar.NvAR_SetF32Array(h, _out("OutputHeadTranslation"), self.head_t, 3), "OutputHeadTranslation")
        _chk(ar.NvAR_SetObject(h, _out("HeadPose"), C.byref(self.head_pose), C.sizeof(Quaternion)), "HeadPose")
        _chk(ar.NvAR_SetObject(h, _out("GazeDirection"), self.gaze_dir, C.sizeof(Point3f)), "GazeDirection")
        _chk(ar.NvAR_SetObject(h, _out("BoundingBoxes"), C.byref(self.bboxes), C.sizeof(BBoxes)), "BoundingBoxes")

    def run(self, frame, out=None):
        """frame: HxWx3 uint8 BGR, C-contiguous. Qaytaradi (out_frame, info)."""
        assert frame.shape == (self.h, self.w, 3) and frame.dtype == np.uint8 and frame.flags.c_contiguous
        if out is None:
            out = np.empty_like(frame)
        cv, ar = self.cv, self.ar
        _chk(cv.NvCVImage_Init(C.byref(self.cpu_in), self.w, self.h, self.w * 3, frame.ctypes.data,
                               NVCV_BGR, NVCV_U8, NVCV_CHUNKY, NVCV_CPU), "Init in")
        _chk(cv.NvCVImage_Transfer(C.byref(self.cpu_in), C.byref(self.gpu_in), 1.0, self.stream,
                                   C.byref(self.tmp)), "Transfer in")
        _chk(ar.NvAR_Run(self.hnd), "Run")
        if self.redirect:
            _chk(cv.NvCVImage_Init(C.byref(self.cpu_out), self.w, self.h, self.w * 3, out.ctypes.data,
                                   NVCV_BGR, NVCV_U8, NVCV_CHUNKY, NVCV_CPU), "Init out")
            _chk(cv.NvCVImage_Transfer(C.byref(self.gpu_out), C.byref(self.cpu_out), 1.0, self.stream,
                                       C.byref(self.tmp)), "Transfer out")
        yaw, pitch, roll = quat_to_euler_deg(self.head_pose)
        # Tartib empirik: kadrni gorizontal aylantirganda [0] o'zgarmaydi (pitch), [1] ishora almashtiradi (yaw).
        # Guide "yaw, pitch" deydi, lekin oyna testi teskarisini ko'rsatdi.
        info = {
            "gaze_pitch": math.degrees(self.gaze[0]), "gaze_yaw": math.degrees(self.gaze[1]),
            "head_yaw": yaw, "head_pitch": pitch, "head_roll": roll,
            "conf": float(np.frombuffer(self.conf, dtype=np.float32).mean()),
            "bbox": (self.rect.x, self.rect.y, self.rect.width, self.rect.height),
            "landmarks": np.frombuffer(self.landmarks, dtype=np.float32).reshape(-1, 2).copy(),
            "gaze_landmarks": np.frombuffer(self.gaze_landmarks, dtype=np.float32).reshape(-1, 2).copy(),
        }
        return out, info

    def close(self):
        if getattr(self, "hnd", None) and self.hnd.value:
            self.ar.NvAR_Destroy(self.hnd)
            self.hnd = C.c_void_p()
        for im in (self.gpu_in, self.gpu_out, self.tmp):
            self.cv.NvCVImage_Dealloc(C.byref(im))
        if self.stream.value:
            self.ar.NvAR_CudaStreamDestroy(self.stream)
            self.stream = C.c_void_p()

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()

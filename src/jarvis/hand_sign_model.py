"""Wrapper ONNX sobre el modelo YOLOX-Nano de deteccion de sellos de mano.

Portado de `model/yolox/yolox_onnx.py` en
https://github.com/Kazuhito00/NARUTO-HandSignDetection (MIT, Copyright (c)
2020 KazuhitoTakahashi - ver `THIRD-PARTY-NOTICES.md` en la raiz del repo).
Sin torch ni tensorflow: preprocesado numpy puro + `onnxruntime`.

`AUDIT.md`/`WORKPLAN.md` de `openspec/changes/hand-sign-fidelity/` documentan
por que se trae este modelo (los sellos de una mano que este proyecto
inventaba no correspondian a ningun sello real) y como se midio (8.1ms/frame
promedio en CPU, mas barato que el `HandLandmarker` que ya corre cada frame).

El modelo emite 16 clases (`output.shape == (1, 3549, 21)`, 21 - 5 = 16). El
demo original indexa `labels.csv` con `class_id + 1`, lo cual lanza
`IndexError` para `class_id == 15` (la ultima clase): `labels.csv` tiene 16
filas (indices 0..15 en una lista 0-indexada), y `15 + 1 == 16` esta fuera de
rango. Ese `+1` solo tiene sentido porque la fila 0 de `labels.csv` es un
"None" de relleno que nunca corresponde a una clase real del modelo. Este
modulo evita el bug entero: `CLASS_NAMES` esta indexada directamente por
`class_id` (sin offset), con la clase 15 (la que el demo original no podia
nombrar sin reventar) mapeada explicitamente a `None`.
"""

from collections import namedtuple

import cv2
import numpy as np
import onnxruntime

# Fila 0 de labels.csv ("None") deliberadamente omitida: index directo por
# class_id (0..15), no class_id + 1 como el demo original.
CLASS_NAMES = (
    "Ne(Rat)",
    "Ushi(Ox)",
    "Tora(Tiger)",
    "U(Hare)",
    "Tatsu(Dragon)",
    "Mi(Snake)",
    "Uma(Horse)",
    "Hitsuji(Ram)",
    "Saru(Monkey)",
    "Tori(Bird)",
    "Inu(Dog)",
    "I(Boar)",
    "Gassho",
    "Unknown",
    "Mizunoe",
    None,  # clase 16 del modelo, sin nombre en labels.csv - la que rompia el demo original
)

INPUT_SHAPE = (416, 416)

# bbox: (x1, y1, x2, y2) en pixeles del frame original.
Detection = namedtuple("Detection", "class_name score bbox")


def class_name_for(class_id):
    """Nombre de clase para `class_id` (0..15), o None si no tiene nombre.

    Nunca lanza `IndexError`: a diferencia del demo original (`class_id + 1`
    contra `labels.csv`), esto indexa `CLASS_NAMES` (16 entradas) directo por
    `class_id`."""
    return CLASS_NAMES[class_id]


class HandSignModel:
    """Detector YOLOX-Nano de sellos de mano sobre un frame ya recortado a
    las 2 manos, o sobre el frame completo (letterbox se encarga del resize)."""

    def __init__(
        self,
        model_path,
        input_shape=INPUT_SHAPE,
        nms_th=0.45,
        nms_score_th=0.1,
        providers=("CUDAExecutionProvider", "CPUExecutionProvider"),
    ):
        self.input_shape = input_shape
        self.nms_th = nms_th
        self.nms_score_th = nms_score_th

        self._session = onnxruntime.InferenceSession(
            str(model_path),
            providers=list(providers),
        )
        self._input_name = self._session.get_inputs()[0].name

    def detect(self, frame):
        """Corre el modelo sobre `frame` (numpy HxWx3) y devuelve la lista de
        `Detection` sobrevivientes a la NMS multiclase (score > nms_score_th),
        ordenadas de mayor a menor score. Filtrar por umbral de confianza final
        (ej. 0.7) es responsabilidad de quien llama (`HandSignTracker`)."""
        image_height, image_width = frame.shape[0], frame.shape[1]
        preprocessed, ratio = self._preprocess(frame)

        outputs = self._session.run(None, {self._input_name: preprocessed[None, :, :, :]})

        bboxes, scores, class_ids = self._postprocess(
            outputs[0],
            ratio,
            image_width,
            image_height,
        )

        detections = [
            Detection(class_name=class_name_for(int(class_id)), score=float(score), bbox=tuple(bbox))
            for bbox, score, class_id in zip(bboxes, scores, class_ids)
        ]
        detections.sort(key=lambda d: d.score, reverse=True)
        return detections

    def _preprocess(self, image, swap=(2, 0, 1)):
        """Letterbox: resize preservando aspect ratio + relleno gris (114)
        hasta `input_shape`, igual que el entrenamiento original de YOLOX."""
        padded_image = np.full((self.input_shape[0], self.input_shape[1], 3), 114, dtype=np.uint8)

        ratio = min(
            self.input_shape[0] / image.shape[0],
            self.input_shape[1] / image.shape[1],
        )
        resized_image = cv2.resize(
            image,
            (int(image.shape[1] * ratio), int(image.shape[0] * ratio)),
            interpolation=cv2.INTER_LINEAR,
        ).astype(np.uint8)

        padded_image[: resized_image.shape[0], : resized_image.shape[1]] = resized_image
        padded_image = padded_image.transpose(swap)
        padded_image = np.ascontiguousarray(padded_image, dtype=np.float32)

        return padded_image, ratio

    def _postprocess(self, outputs, ratio, max_width, max_height):
        """Decodifica la salida cruda (grids/strides 8/16/32) a cajas
        absolutas y aplica NMS multiclase class-agnostic (una caja puede
        competir con cajas de otra clase; nos quedamos con la de mejor score)."""
        strides = (8, 16, 32)
        grids = []
        expanded_strides = []
        for stride in strides:
            hsize = self.input_shape[0] // stride
            wsize = self.input_shape[1] // stride
            xv, yv = np.meshgrid(np.arange(wsize), np.arange(hsize))
            grid = np.stack((xv, yv), 2).reshape(1, -1, 2)
            grids.append(grid)
            expanded_strides.append(np.full((*grid.shape[:2], 1), stride))

        grids = np.concatenate(grids, 1)
        expanded_strides = np.concatenate(expanded_strides, 1)
        outputs[..., :2] = (outputs[..., :2] + grids) * expanded_strides
        outputs[..., 2:4] = np.exp(outputs[..., 2:4]) * expanded_strides

        predictions = outputs[0]
        boxes = predictions[:, :4]
        scores = predictions[:, 4:5] * predictions[:, 5:]

        boxes_xyxy = np.ones_like(boxes)
        boxes_xyxy[:, 0] = boxes[:, 0] - boxes[:, 2] / 2.0
        boxes_xyxy[:, 1] = boxes[:, 1] - boxes[:, 3] / 2.0
        boxes_xyxy[:, 2] = boxes[:, 0] + boxes[:, 2] / 2.0
        boxes_xyxy[:, 3] = boxes[:, 1] + boxes[:, 3] / 2.0
        boxes_xyxy /= ratio

        dets = self._multiclass_nms_class_agnostic(boxes_xyxy, scores)
        if dets is None:
            return [], [], []

        bboxes, scores, class_ids = dets[:, :4], dets[:, 4], dets[:, 5]
        bboxes[:, 0] = np.maximum(0, bboxes[:, 0])
        bboxes[:, 1] = np.maximum(0, bboxes[:, 1])
        bboxes[:, 2] = np.minimum(bboxes[:, 2], max_width)
        bboxes[:, 3] = np.minimum(bboxes[:, 3], max_height)
        return bboxes, scores, class_ids

    def _nms(self, boxes, scores):
        x1, y1, x2, y2 = boxes[:, 0], boxes[:, 1], boxes[:, 2], boxes[:, 3]
        areas = (x2 - x1 + 1) * (y2 - y1 + 1)
        order = scores.argsort()[::-1]

        keep = []
        while order.size > 0:
            i = order[0]
            keep.append(i)
            xx1 = np.maximum(x1[i], x1[order[1:]])
            yy1 = np.maximum(y1[i], y1[order[1:]])
            xx2 = np.minimum(x2[i], x2[order[1:]])
            yy2 = np.minimum(y2[i], y2[order[1:]])

            w = np.maximum(0.0, xx2 - xx1 + 1)
            h = np.maximum(0.0, yy2 - yy1 + 1)
            inter = w * h
            overlap = inter / (areas[i] + areas[order[1:]] - inter)

            inds = np.where(overlap <= self.nms_th)[0]
            order = order[inds + 1]

        return keep

    def _multiclass_nms_class_agnostic(self, boxes, scores):
        cls_inds = scores.argmax(1)
        cls_scores = scores[np.arange(len(cls_inds)), cls_inds]

        valid_mask = cls_scores > self.nms_score_th
        if valid_mask.sum() == 0:
            return None

        valid_scores = cls_scores[valid_mask]
        valid_boxes = boxes[valid_mask]
        valid_cls_inds = cls_inds[valid_mask]
        keep = self._nms(valid_boxes, valid_scores)
        if not keep:
            return None

        return np.concatenate(
            [valid_boxes[keep], valid_scores[keep, None], valid_cls_inds[keep, None]],
            axis=1,
        )

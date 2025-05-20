import cv2
import os
import numpy as np
import time
from collections import Counter

# Caminhos para diferentes classificadores
CASCADE_PATHS = {
    'frontal_default': cv2.data.haarcascades + 'haarcascade_frontalface_default.xml',
    'frontal_alt': cv2.data.haarcascades + 'haarcascade_frontalface_alt.xml',
    'frontal_alt2': cv2.data.haarcascades + 'haarcascade_frontalface_alt2.xml',
    'profile': cv2.data.haarcascades + 'haarcascade_profileface.xml'
}

def apply_image_preprocessing(image):
    """Aplica diferentes pré-processamentos para melhorar a detecção de faces"""
    processed_images = []
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Métodos prioritários primeiro
    processed_images.append(("CLAHE", cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(gray)))
    processed_images.append(("Equalização", cv2.equalizeHist(gray)))
    processed_images.append(("Original", gray))
    
    return processed_images

def non_max_suppression(boxes, overlap_thresh=0.3):
    """Implementa Non-Maximum Suppression para eliminar detecções redundantes"""
    if len(boxes) == 0:
        return []
    
    boxes = np.array(boxes)
    x1 = boxes[:,0]
    y1 = boxes[:,1]
    x2 = x1 + boxes[:,2]
    y2 = y1 + boxes[:,3]
    
    area = (boxes[:,2] + 1) * (boxes[:,3] + 1)
    idxs = np.argsort(y2)
    
    pick = []
    while len(idxs) > 0:
        last = len(idxs) - 1
        i = idxs[last]
        pick.append(i)
        
        xx1 = np.maximum(x1[i], x1[idxs[:last]])
        yy1 = np.maximum(y1[i], y1[idxs[:last]])
        xx2 = np.minimum(x2[i], x2[idxs[:last]])
        yy2 = np.minimum(y2[i], y2[idxs[:last]])
        
        w = np.maximum(0, xx2 - xx1 + 1)
        h = np.maximum(0, yy2 - yy1 + 1)
        
        overlap = (w * h) / area[idxs[:last]]
        
        idxs = np.delete(idxs, np.concatenate(([last],
            np.where(overlap > overlap_thresh)[0])))
    
    return boxes[pick].astype("int")

def process_image(image_path):
    try:
        print(f"Processando: {image_path}")
        
        if not os.path.exists(image_path):
            raise FileNotFoundError(f"Arquivo não encontrado: {image_path}")
            
        img = cv2.imread(image_path)
        if img is None:
            raise ValueError(f"Formato de imagem inválido ou arquivo corrompido: {image_path}")

        result_img = img.copy()
        gray_variants = apply_image_preprocessing(img)

        # Carregar classificadores Haar válidos
        valid_cascades = {
            name: cv2.CascadeClassifier(path)
            for name, path in CASCADE_PATHS.items()
            if os.path.exists(path) and not cv2.CascadeClassifier(path).empty()
        }
        if not valid_cascades:
            raise RuntimeError("Nenhum classificador Haar válido encontrado.")

        # Parâmetros padrão
        detection_params = {
            'scaleFactor': 1.1,
            'minNeighbors': 15,
            'minSize': (150, 150)
        }

        raw_detections = []

        for cascade_name, cascade in valid_cascades.items():
            for prep_name, processed in gray_variants:
                faces = cascade.detectMultiScale(
                    processed,
                    scaleFactor=detection_params['scaleFactor'],
                    minNeighbors=detection_params['minNeighbors'],
                    minSize=detection_params['minSize'],
                    flags=cv2.CASCADE_SCALE_IMAGE
                )
                raw_detections.extend(faces)

        # Aplicar NMS
        all_faces = non_max_suppression(raw_detections, overlap_thresh=0.35)

        # Desenhar resultados
        for (x, y, w, h) in all_faces:
            cv2.rectangle(result_img, (x, y), (x + w, y + h), (0, 255, 0), 5)

        status = f"Faces detectadas: {len(all_faces)}"
        cv2.putText(result_img, status, (10, 30), cv2.FONT_HERSHEY_SIMPLEX,
                    0.7, (0, 255, 0), 2)

        cv2.imwrite(image_path, result_img)
        print(f"[SUCESSO] {len(all_faces)} face(s) detectada(s).")

    except Exception as e:
        print(f"[ERRO CRÍTICO] {str(e)}")
        error_img = np.zeros((300, 500, 3), dtype=np.uint8)
        cv2.putText(error_img, f"ERRO: {str(e)}", (20, 150),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
        cv2.imwrite(image_path, error_img)
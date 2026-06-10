from util.utils import get_som_labeled_img, get_caption_model_processor, get_yolo_model, check_ocr_box
import torch
from PIL import Image
import io
import base64
import time
from typing import Any, Dict
class Omniparser(object):
    def __init__(self, config: Dict):
        self.config = config
        requested_device = str(config.get('device', '')).lower()
        if requested_device == 'cuda' and torch.cuda.is_available():
            device = 'cuda'
        elif requested_device == 'mps' and torch.backends.mps.is_available():
            device = 'mps'
        elif requested_device == 'cpu':
            device = 'cpu'
        elif torch.cuda.is_available():
            device = 'cuda'
        elif torch.backends.mps.is_available():
            device = 'mps'
        else:
            device = 'cpu'

        self.device = device

        self.som_model = get_yolo_model(model_path=config['som_model_path'], device=device)
        self.caption_model_processor = get_caption_model_processor(model_name=config['caption_model_name'], model_name_or_path=config['caption_model_path'], device=device)
        print('Omniparser initialized!!!')

    def parse(self, image_base64: str, include_image: bool = False) -> Dict[str, Any]:
        decode_start = time.time()
        image_bytes = base64.b64decode(image_base64)
        image = Image.open(io.BytesIO(image_bytes))
        decode_duration = time.time() - decode_start
        print('image size:', image.size)
        
        box_overlay_ratio = max(image.size) / 3200
        draw_bbox_config = {
            'text_scale': 0.8 * box_overlay_ratio,
            'text_thickness': max(int(2 * box_overlay_ratio), 1),
            'text_padding': max(int(3 * box_overlay_ratio), 1),
            'thickness': max(int(3 * box_overlay_ratio), 1),
        }

        ocr_start = time.time()
        (text, ocr_bbox), _ = check_ocr_box(image, display_img=False, output_bb_format='xyxy', easyocr_args={'text_threshold': 0.8}, use_paddleocr=False)
        ocr_duration = time.time() - ocr_start

        som_image_base64, label_coordinates, parsed_content_list, parse_timings = get_som_labeled_img(
            image,
            self.som_model,
            BOX_TRESHOLD=self.config['BOX_TRESHOLD'],
            output_coord_in_ratio=True,
            ocr_bbox=ocr_bbox,
            draw_bbox_config=draw_bbox_config,
            caption_model_processor=self.caption_model_processor,
            ocr_text=text,
            use_local_semantics=True,
            iou_threshold=0.7,
            scale_img=False,
            batch_size=128,
            device=self.device,
            include_image=include_image,
        )

        return {
            'som_image_base64': som_image_base64,
            'parsed_content_list': parsed_content_list,
            'timings': {
                'decode_image_s': decode_duration,
                'ocr_s': ocr_duration,
                **parse_timings,
            },
        }
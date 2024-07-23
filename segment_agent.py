import numpy as np
from segment_anything import sam_model_registry, SamAutomaticMaskGenerator, SamPredictor
from utils.slider_action import SliderAction


class SegmentAgent:
    """Used to generate image masks from an inputted image and points on the image"""

    def __init__(self):
        sam_checkpoint = "./sam_checkpoints/sam_vit_b_01ec64.pth"
        self.last_logits = None
        self.last_scores = None
        model_type = "vit_b"
        device = "cuda"
        self.sam = sam_model_registry[model_type](checkpoint=sam_checkpoint)
        self.sam.to(device=device)
        self.predictor = SamPredictor(self.sam)
        self.mask_level = SliderAction.AUTO

    def setImage(self, image_array):
        self.predictor.set_image(image_array)

    def generateMaskFromPoint(self, x, y):
        input_point = np.array([[x, y]])
        input_label = np.array([1])
        masks, scores, logits = self.predictor.predict(
            point_coords=input_point,
            point_labels=input_label,
            multimask_output=True,
        )
        self.last_logits = logits
        self.last_scores = scores
        bestMask = self.getBestMask(masks, scores)
        return bestMask

    def generateMaskFromPoints(self, points):
        input_point = np.array([point[0] for point in points])
        input_label = np.array([point[1] for point in points])
        masks, scores, logits = self.predictor.predict(
            point_coords=input_point,
            point_labels=input_label,
            multimask_output=True,
        )
        self.last_logits = logits
        self.last_scores = scores
        bestMask = self.getBestMask(masks, scores)
        return bestMask

    def getBestMask(self, masks: list, scores: list) -> list:
        if self.mask_level == SliderAction.AUTO:
            bestScore = 0
            bestMask = None
            for _, (mask, score) in enumerate(zip(masks, scores)):
                if score > bestScore:
                    bestScore = score
                    bestMask = mask
            return bestMask
        else:
            return masks[(self.mask_level.value) * -1]

    def segmentAll(self):
        mask_generator = SamAutomaticMaskGenerator(
            model=self.sam,
            points_per_side=64,
            points_per_batch=5,
            pred_iou_thresh=0.86,
            stability_score_thresh=0.92,
            crop_n_points_downscale_factor=2,
            min_mask_region_area=100,
        )
        masks = mask_generator.generate(self.image)
        return masks

    def set_mask_level(self, mask_level: SliderAction):
        self.mask_level = mask_level

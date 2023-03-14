from __future__ import annotations

from typing import Optional

import numpy as np

from ...group import group
from ...impl.external_stable_diffusion import (
    RESIZE_MODE_LABELS,
    SAMPLER_NAME_LABELS,
    STABLE_DIFFUSION_IMG2IMG_PATH,
    ResizeMode,
    SamplerName,
    decode_base64_image,
    encode_base64_image,
    nearest_valid_size,
    post,
    verify_api_connection,
)
from ...node_base import NodeBase
from ...node_cache import cached
from ...node_factory import NodeFactory
from ...properties.inputs import (
    BoolInput,
    EnumInput,
    ImageInput,
    SeedInput,
    SliderInput,
    TextAreaInput,
)
from ...properties.outputs import ImageOutput
from ...utils.seed import Seed
from ...utils.utils import get_h_w_c
from . import category as ExternalStableDiffusionCategory

verify_api_connection()


@NodeFactory.register("chainner:external_stable_diffusion:img2img")
class Img2Img(NodeBase):
    def __init__(self):
        super().__init__()
        self.description = "Modify an image using Automatic1111"
        self.inputs = [
            ImageInput(),
            TextAreaInput("Prompt").make_optional(),
            TextAreaInput("Negative Prompt").make_optional(),
            SliderInput(
                "Denoising Strength",
                minimum=0,
                default=0.75,
                maximum=1,
                slider_step=0.01,
                controls_step=0.1,
                precision=2,
            ),
            group("seed")(SeedInput()),
            SliderInput("Steps", minimum=1, default=20, maximum=150),
            EnumInput(
                SamplerName,
                default_value=SamplerName.EULER,
                option_labels=SAMPLER_NAME_LABELS,
            ),
            SliderInput(
                "CFG Scale",
                minimum=1,
                default=7,
                maximum=20,
                controls_step=0.1,
                precision=1,
            ),
            EnumInput(
                ResizeMode,
                default_value=ResizeMode.JUST_RESIZE,
                option_labels=RESIZE_MODE_LABELS,
            ).with_id(10),
            SliderInput(
                "Width",
                minimum=64,
                default=512,
                maximum=2048,
                slider_step=8,
                controls_step=8,
            ).with_id(8),
            SliderInput(
                "Height",
                minimum=64,
                default=512,
                maximum=2048,
                slider_step=8,
                controls_step=8,
            ).with_id(9),
            BoolInput("Seamless Edges", default=False),
        ]
        self.outputs = [
            ImageOutput(
                image_type="""def nearest_valid(n: number) = int & floor(n / 8) * 8;
                Image {
                    width: nearest_valid(Input8),
                    height: nearest_valid(Input9)
                }""",
                channels=3,
            ),
        ]

        self.category = ExternalStableDiffusionCategory
        self.name = "Image to Image"
        self.icon = "MdChangeCircle"
        self.sub = "Automatic1111"

    @cached
    def run(
        self,
        image: np.ndarray,
        prompt: Optional[str],
        negative_prompt: Optional[str],
        denoising_strength: float,
        seed: Seed,
        steps: int,
        sampler_name: SamplerName,
        cfg_scale: float,
        resize_mode: ResizeMode,
        width: int,
        height: int,
        tiling: bool,
    ) -> np.ndarray:
        width, height = nearest_valid_size(
            width, height
        )  # This cooperates with the "image_type" of the ImageOutput
        request_data = {
            "init_images": [encode_base64_image(image)],
            "prompt": prompt or "",
            "negative_prompt": negative_prompt or "",
            "denoising_strength": denoising_strength,
            "seed": seed.to_u32(),
            "steps": steps,
            "sampler_name": sampler_name.value,
            "cfg_scale": cfg_scale,
            "width": width,
            "height": height,
            "resize_mode": resize_mode.value,
            "tiling": tiling,
        }
        response = post(path=STABLE_DIFFUSION_IMG2IMG_PATH, json_data=request_data)
        result = decode_base64_image(response["images"][0])
        h, w, _ = get_h_w_c(result)
        assert (w, h) == (
            width,
            height,
        ), f"Expected the returned image to be {width}x{height}px but found {w}x{h}px instead "
        return result
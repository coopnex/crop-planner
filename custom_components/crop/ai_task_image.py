"""AI task entity for generating plant images."""

from __future__ import annotations

import pathlib
import shutil
from typing import TYPE_CHECKING
from urllib.parse import urlparse

import voluptuous as vol
from homeassistant.components.ai_task import (
    AITaskEntity,
    AITaskEntityFeature,
    GenDataTask,
    GenDataTaskResult,
    async_generate_data,
    async_generate_image,
)
from homeassistant.const import Platform
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.entity import async_generate_entity_id

from .ai_task_helpers import _find_delegate_entity_id, _find_image_delegate_entity_id
from .const import COORDINATOR, DOMAIN, LOGGER, AIState

if TYPE_CHECKING:
    from homeassistant.components.conversation import ChatLog
    from homeassistant.core import HomeAssistant

    from .coordinator import CropPlannerConfigEntry, CropPlannerCoordinator

_IMAGE_PROMPT_INSTRUCTIONS = (
    "You are a botanical photographer's assistant. "
    "Given a plant name, write a concise image generation prompt (max 40 words) "
    "that will produce a close-up, centered photograph of the plant's most "
    "recognisable fruit or flower. "
    "The subject should fill the frame against a neutral background. "
    "Be specific about the species and the part of the plant to depict. "
    "Return your prompt in the 'response' field."
)

_IMAGE_PROMPT_SCHEMA = vol.Schema({vol.Required("response"): str})


class GeneratePlantImageAITask(AITaskEntity):
    """
    AI task entity that generates a plant image using an AI image generation model.

    Workflow:
    1. Ask the configured LLM to craft a focused botanical image-generation prompt.
    2. Delegate to a GENERATE_IMAGE-capable ai_task entity.
    3. Copy the returned image from the HA media store to www/crop_planner/ so
       the URL is permanent (the signed media-source URL expires after ~1 hour).
    4. Return the /local/ URL so it can be stored on the crop entity.
    """

    _attr_should_poll = False
    _attr_supported_features = AITaskEntityFeature.GENERATE_DATA
    _attr_has_entity_name = True
    _attr_translation_key = "generate_plant_image"

    def __init__(self, hass: HomeAssistant, entry: CropPlannerConfigEntry) -> None:
        """Initialise the entity."""
        coordinator: CropPlannerCoordinator = hass.data[DOMAIN][COORDINATOR]
        self._hass = hass
        self._entry = entry
        self._coordinator = coordinator
        self._attr_unique_id = f"{entry.entry_id}_generate_plant_image"
        self._device_id = coordinator.device_id
        self.entity_id = async_generate_entity_id(
            f"{Platform.AI_TASK}.{{}}", "crop generate plant image", current_ids={}
        )

    async def _async_generate_data(
        self,
        task: GenDataTask,
        chat_log: ChatLog,  # noqa: ARG002
    ) -> GenDataTaskResult:
        """Generate a plant image and return its permanent /local/ URL."""
        plant_name = (task.instructions or "").strip()
        if not plant_name:
            msg = "No plant name provided. Pass it via the instructions field."
            raise HomeAssistantError(msg)
        self._coordinator.set_ai_state(AIState.GENERATING_IMAGE)
        try:
            image_prompt = await self._inner_generate_image_prompt(plant_name, task)
            image_url = await self._inner_generate_image(image_prompt, task)
            return GenDataTaskResult(
                conversation_id=None,
                data={"plant_name": plant_name, "image_url": image_url},
            )
        finally:
            self._coordinator.set_ai_state(AIState.IDLE)

    async def _inner_generate_image_prompt(
        self, plant_name: str, task: GenDataTask
    ) -> str:
        """Ask the text LLM to craft a focused botanical image-generation prompt."""
        text_delegate = _find_delegate_entity_id(self._hass)
        if text_delegate is None:
            msg = "No text AI task entity available to build the image prompt."
            raise HomeAssistantError(msg)

        prompt_result = await async_generate_data(
            self._hass,
            task_name=task.name,
            entity_id=text_delegate,
            instructions=f"{_IMAGE_PROMPT_INSTRUCTIONS}\n\nPlant name: {plant_name}",
            structure=_IMAGE_PROMPT_SCHEMA,
        )
        image_prompt: str = ((prompt_result.data or {}).get("response") or "").strip()
        if not image_prompt:
            image_prompt = (
                f"Close-up centered photograph of {plant_name} fruit or flower, "
                "filling the frame, neutral background, sharp detail."
            )
        LOGGER.debug("Image generation prompt for %r: %s", plant_name, image_prompt)
        return image_prompt

    async def _inner_generate_image(
        self, image_prompt: str, task: GenDataTask
    ) -> str | None:
        """Delegate image generation and persist the result, returning a /local/ URL."""
        image_delegate = _find_image_delegate_entity_id(self._hass)
        if image_delegate is None:
            msg = (
                "No image-generation AI task entity available. "
                "Set up an AI integration that supports image generation "
                "(e.g. Google AI with an image model) first."
            )
            raise HomeAssistantError(msg)

        image_result = await async_generate_image(
            self._hass,
            task_name=task.name,
            entity_id=image_delegate,
            instructions=image_prompt,
        )
        if not image_result:
            msg = "Image generation returned no data."
            raise HomeAssistantError(msg)
        # async_generate_image returns a ServiceResponse dict with a signed 'url'
        # that expires after ~1 hour. Copy the file to www/crop_planner/ so the
        # /local/ URL is permanent.
        signed_url: str | None = image_result.get("url")
        if not signed_url:
            msg = "Image generation returned no URL."
            raise HomeAssistantError(msg)

        image_url = await self._hass.async_add_executor_job(
            self._persist_image, signed_url
        )
        LOGGER.debug("Generated image for %r: %s", image_prompt, image_url)
        return image_url

    def _persist_image(self, signed_url: str) -> str:
        """
        Copy the generated image to www/crop_planner/ and return the /local/ URL.

        Runs in an executor thread because it performs blocking file I/O.
        """
        # async_sign_path returns /media/local/ai_task/image/<filename>.png?authSig=...
        # The file lives at config_dir/media/local/ai_task/image/<filename>.png,
        # so strip the leading /media/ before joining with config_dir/media/.
        url_path = urlparse(signed_url).path
        rel_path = url_path.removeprefix("/media/")
        filename = pathlib.Path(rel_path).name
        src = pathlib.Path(self._hass.config.config_dir) / "media" / rel_path
        dst_dir = pathlib.Path(self._hass.config.config_dir) / "www" / "crop_planner"
        dst_dir.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst_dir / filename)
        return f"/local/crop_planner/{filename}"

    def update_registry(self) -> None:
        """Associate the entity with the integration device."""
        erreg = er.async_get(self._hass)
        erreg.async_update_entity(self.entity_id, device_id=self._device_id)

    async def async_added_to_hass(self) -> None:
        """Register in entity registry once added to hass."""
        self.update_registry()

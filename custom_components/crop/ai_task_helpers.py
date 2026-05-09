"""Shared helpers for AI task entities."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from homeassistant.components.ai_task import AITaskEntityFeature
from homeassistant.components.ai_task.const import DATA_COMPONENT
from homeassistant.const import Platform
from homeassistant.helpers import entity_registry as er

from .const import CROP_PHASES, CROP_PLATFORM, DOMAIN

if TYPE_CHECKING:
    from homeassistant.core import HomeAssistant


def _build_context(
    hass: HomeAssistant, crops: list[dict[str, Any]], todos: list[dict[str, Any]]
) -> str:
    """Serialise current crop state into a human-readable block for the LLM."""
    today = datetime.now(tz=UTC).date().isoformat()
    language = hass.config.language
    latitude = hass.config.latitude
    longitude = hass.config.longitude
    entity_registry = er.async_get(hass)
    lines = [f"* Today is {today}."]
    lines.append(f"* User language: {language}.")
    lines.append(f"* Location: (latitude {latitude:.4f}, longitude {longitude:.4f}).")
    if crops:
        lines.append("* Current crops:")
        for crop in crops:
            entity_id = entity_registry.async_get_entity_id(
                CROP_PLATFORM, DOMAIN, crop["id"]
            )
            line = _build_crop_context(crop, entity_id)
            lines.append(f"  - {line}")
    if todos:
        lines.append("* Current todos:")
        for todo in todos:
            summary = todo.get("summary")
            description = f"({todo.get('description') or ''})"
            lines.append(f"  - {summary} {description}")

    return "\n".join(lines)


def _build_crop_context(crop: dict[str, Any], entity_id: str | None = None) -> str:
    """Serialise a single crop into a human-readable line for the LLM."""
    name = crop.get("name", "Unknown")
    species = crop.get("species") or None
    qty = crop.get("quantity", 1)

    phases: dict[str, dict] = crop.get("phases", {})
    phase_parts = []
    for phase in CROP_PHASES:
        if phase in phases:
            p = phases[phase]
            start = p.get("start", "")
            end = p.get("end", "")
            if start or end:
                phase_parts.append(f"{phase}: {start or '?'} → {end or '?'}")
    species_str = f" ({species})" if species else ""
    entity_str = f"; entity_id: {entity_id}" if entity_id else ""
    phase_str = f"; phases: {', '.join(phase_parts)}" if phase_parts else ""
    return f"{name}{species_str}: qty {qty}{entity_str}{phase_str}"


def _find_delegate_entity_id(hass: HomeAssistant) -> str | None:
    """Return an ai_task entity supporting GENERATE_DATA, excluding our own entities."""
    return _find_delegate_entity_id_for_feature(hass, AITaskEntityFeature.GENERATE_DATA)


def _find_image_delegate_entity_id(hass: HomeAssistant) -> str | None:
    """Return an ai_task entity supporting GENERATE_IMAGE, excluding ours."""
    return _find_delegate_entity_id_for_feature(
        hass, AITaskEntityFeature.GENERATE_IMAGE
    )


def _find_delegate_entity_id_for_feature(
    hass: HomeAssistant, feature: AITaskEntityFeature
) -> str | None:
    """Return the first external ai_task entity that supports *feature*."""
    entity_registry = er.async_get(hass)
    our_entity_ids = {
        entry.entity_id
        for entry in entity_registry.entities.values()
        if entry.domain == Platform.AI_TASK and entry.platform == DOMAIN
    }
    component = hass.data.get(DATA_COMPONENT)
    if component is None:
        return None
    for entity in component.entities:
        if (
            entity.entity_id not in our_entity_ids
            and feature in entity.supported_features
        ):
            return entity.entity_id
    return None

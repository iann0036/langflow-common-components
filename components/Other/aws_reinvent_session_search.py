# pyright: reportCallIssue=false
from __future__ import annotations

import json
import re
from typing import Any

import requests
from lfx.custom.custom_component.component import Component
from lfx.io import IntInput, MessageTextInput, Output, StrInput
from lfx.schema.data import Data


class AWSReInventSessionSearch(Component):
    """Search the public AWS re:Invent catalog and return structured session matches."""

    display_name = "AWS re:Invent Session Search"
    description = "Searches the public AWS re:Invent catalog and returns details for matching sessions."
    documentation: str = "https://docs.aws.amazon.com/events/latest/devguide/rest-api.html"
    icon = "Amazon"
    name = "AWSReInventSessionSearch"

    CATALOG_PAGE_TEMPLATE = (
        "https://registration.awsevents.com/flow/awsevents/{event_identifier}/"
        "eventcatalog/page/eventcatalog"
    )
    SESSIONS_API_TEMPLATE = "https://events-api.aws/v1/events/{event_identifier}/sessions"
    USER_AGENT = "langflow-common-components/aws-reinvent-session-search"
    TOPIC_ATTRIBUTES = (
        "Topic",
        "Area of Interest",
        "AreaofInterest",
        "Track",
        "Services",
        "Primary Topic",
    )

    inputs: list[Any] = [
        MessageTextInput(
            name="search_query",
            display_name="Search Query",
            info="The keyword, phrase, or session code to search for.",
            required=True,
            tool_mode=True,
        ),
        IntInput(
            name="max_results",
            display_name="Max Results",
            info="The maximum number of matching sessions to return.",
            value=5,
            required=True,
            tool_mode=True,
        ),
        IntInput(
            name="page_size",
            display_name="Page Size",
            info="The number of catalog sessions to request per API page.",
            value=100,
            advanced=True,
        ),
        StrInput(
            name="event_identifier",
            display_name="Event Identifier",
            info="The AWS event identifier used by the AWS Events API.",
            value="reinvent2026",
            advanced=True,
        ),
        StrInput(
            name="browser_timezone",
            display_name="Browser Timezone",
            info="Legacy setting retained for compatibility; the official AWS Events API does not use it.",
            value="America/Los_Angeles",
            advanced=True,
        ),
    ]

    outputs = [
        Output(display_name="Sessions", name="output", method="search_sessions"),
    ]

    def _catalog_page_url(self) -> str:
        event_identifier = str(self.event_identifier or "reinvent2026").strip()
        return self.CATALOG_PAGE_TEMPLATE.format(event_identifier=event_identifier)

    def _sessions_api_url(self) -> str:
        event_identifier = str(self.event_identifier or "reinvent2026").strip()
        return self.SESSIONS_API_TEMPLATE.format(event_identifier=event_identifier)

    def _fetch_page(self, next_token: str | None, size: int) -> tuple[list[dict], str | None]:
        headers = {
            "Accept": "application/json",
            "User-Agent": self.USER_AGENT,
        }
        params = {
            "pageSize": str(size),
        }
        if next_token:
            params["nextToken"] = next_token

        response = requests.get(
            self._sessions_api_url(),
            headers=headers,
            params=params,
            timeout=60,
        )
        if response.status_code == 404:
            msg = "AWS Events API sessions endpoint was not available for this event."
            raise RuntimeError(msg)
        response.raise_for_status()
        payload = response.json()

        if isinstance(payload, list):
            return list(payload), None
        if isinstance(payload, dict):
            if "sessions" in payload:
                return list(payload.get("sessions", []) or []), payload.get("nextToken")
            if "items" in payload:
                return list(payload.get("items", []) or []), payload.get("nextToken")
            if "sectionList" in payload and payload["sectionList"]:
                section = payload["sectionList"][0]
                return list(section.get("items", []) or []), section.get("nextToken") or payload.get("nextToken")

        msg = "Unexpected response from the AWS Events API."
        raise ValueError(msg)

    @staticmethod
    def _sort_matches(matches: list[dict[str, Any]]) -> None:
        matches.sort(key=lambda item: (-item["match_score"], item.get("code") or "", item.get("title") or ""))

    def _search_catalog_sessions(self, query: str, max_results: int) -> tuple[list[dict], int]:
        page_size = max(1, int(self.page_size or 100))

        matches: list[dict] = []
        seen_ids: set[str] = set()
        next_token: str | None = None
        scanned_sessions = 0

        while True:
            items, next_token = self._fetch_page(next_token, page_size)
            if not items:
                break

            page_matches: list[dict[str, Any]] = []
            for item in items:
                session_id = str(
                    item.get("code")
                    or item.get("sessionCode")
                    or item.get("abbreviation")
                    or item.get("sessionId")
                    or item.get("sessionID")
                    or item.get("id")
                    or ""
                )
                if session_id and session_id in seen_ids:
                    continue
                if session_id:
                    seen_ids.add(session_id)
                scanned_sessions += 1
                score = self._match_score(item, query)
                if score > 0:
                    page_matches.append(self._session_details(item, score))

            if page_matches:
                matches.extend(page_matches)
                self._sort_matches(matches)
                if len(matches) > max_results:
                    del matches[max_results:]
            if not next_token:
                break

        return matches, scanned_sessions

    @staticmethod
    def _normalize(value: Any) -> str:
        return re.sub(r"\s+", " ", str(value or "").strip()).lower()

    @staticmethod
    def _string_values(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            stripped = value.strip()
            return [stripped] if stripped else []
        if isinstance(value, dict):
            for key in ("name", "title", "label", "value", "displayName"):
                nested_value = value.get(key)
                if nested_value:
                    return AWSReInventSessionSearch._string_values(nested_value)
            return []
        if isinstance(value, list):
            values: list[str] = []
            for item in value:
                values.extend(AWSReInventSessionSearch._string_values(item))
            return values
        stripped = str(value).strip()
        return [stripped] if stripped else []

    @staticmethod
    def _attribute_map(item: dict) -> dict[str, list[str]]:
        attributes: dict[str, list[str]] = {}
        for attribute in item.get("attributevalues", []) or []:
            name = str(attribute.get("attribute") or "").strip()
            value = str(attribute.get("value") or "").strip()
            if name and value:
                attributes.setdefault(name, []).append(value)

        field_mappings = {
            "Type": ("type", "sessionType"),
            "Level": ("level", "sessionLevel"),
            "Topic": ("topic", "topics", "categories", "tracks", "services", "primaryTopic"),
        }
        for attribute_name, field_names in field_mappings.items():
            collected_values: list[str] = []
            for field_name in field_names:
                collected_values.extend(AWSReInventSessionSearch._string_values(item.get(field_name)))
            if collected_values:
                deduplicated_values = list(dict.fromkeys(collected_values))
                existing_values = attributes.setdefault(attribute_name, [])
                for value in deduplicated_values:
                    if value not in existing_values:
                        existing_values.append(value)
        return attributes

    @classmethod
    def _topic(cls, attributes: dict[str, list[str]]) -> str | None:
        for attribute_name in cls.TOPIC_ATTRIBUTES:
            values = attributes.get(attribute_name)
            if values:
                return ", ".join(values)
        return None

    @staticmethod
    def _speakers(item: dict) -> list[str]:
        speakers = []
        seen_speakers: set[str] = set()
        for key in ("speakers", "speakerList", "participants"):
            value = item.get(key)
            if isinstance(value, list):
                for speaker in value:
                    name = None
                    if isinstance(speaker, dict):
                        name = str(
                            speaker.get("name")
                            or speaker.get("fullName")
                            or speaker.get("displayName")
                            or speaker.get("speakerName")
                            or speaker.get("participantName")
                        )
                    elif speaker:
                        name = str(speaker)

                    normalized_name = name.strip() if name else ""
                    if normalized_name and normalized_name not in seen_speakers:
                        seen_speakers.add(normalized_name)
                        speakers.append(normalized_name)
        return speakers

    def _match_score(self, item: dict, query: str) -> int:
        normalized_query = self._normalize(query)
        if not normalized_query:
            return 0

        attributes = self._attribute_map(item)
        code = str(
            item.get("code")
            or item.get("sessionCode")
            or item.get("abbreviation")
            or item.get("sessionId")
            or item.get("sessionID")
            or item.get("id")
            or ""
        )
        title = str(item.get("title") or item.get("name") or "")
        abstract = str(item.get("abstract") or item.get("description") or item.get("summary") or "")
        topic = self._topic(attributes) or ""
        level = " ".join(attributes.get("Level", []))
        session_type = str(item.get("type") or item.get("sessionType") or ", ".join(attributes.get("Type", [])) or "")
        speakers = " ".join(self._speakers(item))
        searchable = self._normalize(
            " ".join(
                [
                    code,
                    title,
                    abstract,
                    topic,
                    level,
                    session_type,
                    speakers,
                    " ".join(f"{name} {' '.join(values)}" for name, values in attributes.items()),
                ]
            )
        )

        tokens = [token for token in re.split(r"\W+", normalized_query) if token]
        if not tokens:
            return 0

        exact_code = self._normalize(code) == normalized_query
        exact_title = self._normalize(title) == normalized_query
        phrase_in_title = normalized_query in self._normalize(title)
        phrase_in_searchable = normalized_query in searchable
        matched_tokens = sum(1 for token in tokens if token in searchable)

        if not (exact_code or exact_title or phrase_in_searchable or matched_tokens == len(tokens)):
            return 0

        score = matched_tokens * 10
        if exact_code:
            score += 100
        if exact_title:
            score += 90
        if phrase_in_title:
            score += 50
        elif phrase_in_searchable:
            score += 25
        return score

    def _session_details(self, item: dict, match_score: int) -> dict[str, Any]:
        attributes = self._attribute_map(item)
        code = str(
            item.get("code")
            or item.get("sessionCode")
            or item.get("abbreviation")
            or item.get("sessionId")
            or item.get("sessionID")
            or item.get("id")
            or ""
        )
        return {
            "id": str(item.get("sessionId") or item.get("sessionID") or item.get("id") or code),
            "code": code,
            "title": item.get("title") or item.get("name"),
            "abstract": item.get("abstract") or item.get("description") or item.get("summary"),
            "type": item.get("type") or item.get("sessionType") or ", ".join(attributes.get("Type", [])),
            "level": item.get("level") or item.get("sessionLevel") or ", ".join(attributes.get("Level", [])),
            "topic": self._topic(attributes),
            "speakers": self._speakers(item),
            "attributes": attributes,
            "catalog_page": self._catalog_page_url(),
            "match_score": match_score,
        }

    def search_sessions(self) -> Data:
        query = str(self.search_query or "").strip()
        if not query:
            msg = "Search Query is required."
            raise ValueError(msg)

        max_results = max(1, int(self.max_results or 5))
        matches, scanned_sessions = self._search_catalog_sessions(query, max_results)

        result = {
            "query": query,
            "match_count": len(matches),
            "scanned_sessions": scanned_sessions,
            "sessions": matches,
        }
        self.status = f"Found {len(matches)} AWS re:Invent session matches"
        return Data(text=json.dumps(result, indent=2, sort_keys=True), data=result)

# pyright: reportCallIssue=false
from __future__ import annotations

import json
import os
import re
from typing import Any
from urllib.parse import quote

import requests
from lfx.custom.custom_component.component import Component
from lfx.io import IntInput, MessageTextInput, Output, StrInput
from lfx.schema.data import Data


class AWSReInventSessionSearch(Component):
    """Search the authenticated AWS re:Invent 2026 catalog and return structured session matches."""

    display_name = "AWS re:Invent 2026 Session Search"
    description = "Searches the authenticated AWS re:Invent 2026 catalog only and returns details for matching sessions."
    documentation: str = "https://docs.aws.amazon.com/events/latest/devguide/rest-api.html"
    icon = "Amazon"
    name = "AWSReInventSessionSearch"
    EVENT_IDENTIFIER = "reinvent2026"

    CATALOG_PAGE_TEMPLATE = (
        "https://registration.awsevents.com/flow/awsevents/{event_identifier}/"
        "eventcatalog/page/eventcatalog"
    )
    SESSIONS_API_TEMPLATE = "https://api.awsevents.com/v1/events/{event_identifier}/sessions"
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
            name="auth_token_env_var",
            display_name="Auth Token Environment Variable",
            info="Environment variable name that stores the AWS re:Invent 2026 Authorization header value or raw bearer token.",
            value="AWS_REINVENT_AUTH_TOKEN",
            required=True,
            tool_mode=True,
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
        return self.CATALOG_PAGE_TEMPLATE.format(event_identifier=self._event_identifier())

    def _sessions_api_url(self) -> str:
        return self.SESSIONS_API_TEMPLATE.format(event_identifier=self._event_identifier())

    def _event_identifier(self) -> str:
        return quote(self.EVENT_IDENTIFIER, safe="")

    @staticmethod
    def _input_value(value: Any) -> str:
        return str(value or "").strip()

    def _auth_token(self) -> str:
        env_var_name = self._auth_token_env_var_name()
        auth_token = self._input_value(os.getenv(env_var_name))
        if not auth_token:
            msg = f"AWS re:Invent 2026 requires the auth token environment variable '{env_var_name}' to be set."
            raise ValueError(msg)
        return auth_token

    def _auth_token_env_var_name(self) -> str:
        return self._input_value(self.auth_token_env_var) or "AWS_REINVENT_AUTH_TOKEN"

    def _auth_headers(self) -> dict[str, str]:
        auth_token = self._auth_token()
        if " " in auth_token:
            return {
                "Authorization": auth_token,
            }
        bearer_prefix = "Bearer "
        return {
            "Authorization": bearer_prefix + auth_token,
        }

    def _fetch_page(
        self,
        auth_headers: dict[str, str],
        next_token: str | None,
        size: int,
    ) -> tuple[list[dict], str | None]:
        headers = {
            "Accept": "application/json",
            "User-Agent": self.USER_AGENT,
            **auth_headers,
        }
        params = {
            "pageSize": size,
        }
        if next_token:
            params["nextToken"] = next_token

        response = requests.get(
            self._sessions_api_url(),
            headers=headers,
            params=params,
            timeout=60,
        )
        if response.status_code in (401, 403):
            env_var_name = self._auth_token_env_var_name()
            msg = (
                f"AWS re:Invent 2026 authentication failed. Check that the auth token environment variable "
                f"'{env_var_name}' is set and contains a valid, unexpired Authorization header value or bearer token."
            )
            raise RuntimeError(msg)
        if response.status_code == 404:
            msg = "AWS Events API sessions endpoint was not available for this event."
            raise RuntimeError(msg)
        response.raise_for_status()
        payload = response.json()

        if isinstance(payload, list):
            return list(payload), None
        if isinstance(payload, dict):
            if "sessions" in payload:
                sessions = payload.get("sessions", []) or []
                if isinstance(sessions, list):
                    return list(sessions), payload.get("nextToken")
            if "items" in payload:
                items = payload.get("items", []) or []
                if isinstance(items, list):
                    return list(items), payload.get("nextToken")
            if "sectionList" in payload and payload["sectionList"]:
                collected_items: list[dict] = []
                next_section_token = payload.get("nextToken")
                for section in payload["sectionList"]:
                    if not isinstance(section, dict):
                        continue
                    items = section.get("items", []) or []
                    if not isinstance(items, list):
                        continue
                    collected_items.extend(items)
                    if not next_section_token:
                        next_section_token = section.get("nextToken")
                if collected_items:
                    return collected_items, next_section_token

        msg = "Unexpected response from the AWS Events API."
        raise ValueError(msg)

    @staticmethod
    def _sort_matches(matches: list[dict[str, Any]]) -> None:
        matches.sort(key=lambda item: (-item["match_score"], item.get("code") or "", item.get("title") or ""))

    @staticmethod
    def _session_code(item: dict) -> str:
        return str(
            item.get("code")
            or item.get("sessionCode")
            or item.get("abbreviation")
            or item.get("sessionId")
            or item.get("sessionID")
            or item.get("id")
            or ""
        )

    @classmethod
    def _session_identifier(cls, item: dict) -> str:
        return str(item.get("sessionId") or item.get("sessionID") or item.get("id") or cls._session_code(item))

    @staticmethod
    def _session_title(item: dict) -> str:
        return str(item.get("title") or item.get("name") or "")

    @staticmethod
    def _session_abstract(item: dict) -> str:
        return str(item.get("abstract") or item.get("description") or item.get("summary") or "")

    @staticmethod
    def _session_type(item: dict, attributes: dict[str, list[str]]) -> str:
        return str(item.get("type") or item.get("sessionType") or ", ".join(attributes.get("Type", [])) or "")

    @staticmethod
    def _session_level(item: dict, attributes: dict[str, list[str]]) -> str:
        return str(item.get("level") or item.get("sessionLevel") or ", ".join(attributes.get("Level", [])) or "")

    def _search_catalog_sessions(self, query: str, max_results: int) -> tuple[list[dict], int]:
        page_size = max(1, int(self.page_size or 100))
        auth_headers = self._auth_headers()

        matches: list[dict] = []
        seen_ids: set[str] = set()
        next_token: str | None = None
        scanned_sessions = 0

        while True:
            items, next_token = self._fetch_page(auth_headers, next_token, page_size)
            if not items:
                break

            page_matches: list[dict[str, Any]] = []
            for item in items:
                session_id = self._session_identifier(item)
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
    def _append_unique_strings(values: list[str], seen_values: set[str], new_values: list[str]) -> None:
        for string_value in new_values:
            if string_value not in seen_values:
                seen_values.add(string_value)
                values.append(string_value)

    @staticmethod
    def _string_values(value: Any) -> list[str]:
        if value is None:
            return []
        if isinstance(value, str):
            stripped = value.strip()
            return [stripped] if stripped else []
        if isinstance(value, dict):
            values: list[str] = []
            seen_values: set[str] = set()
            for key in ("name", "title", "label", "value", "displayName"):
                nested_value = value.get(key)
                if nested_value:
                    AWSReInventSessionSearch._append_unique_strings(
                        values,
                        seen_values,
                        AWSReInventSessionSearch._string_values(nested_value),
                    )
            return values
        if isinstance(value, list):
            values: list[str] = []
            seen_values: set[str] = set()
            for item in value:
                AWSReInventSessionSearch._append_unique_strings(
                    values,
                    seen_values,
                    AWSReInventSessionSearch._string_values(item),
                )
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
                seen_values = set(attributes.get(attribute_name, []))
                existing_values = attributes.setdefault(attribute_name, [])
                for value in collected_values:
                    if value not in seen_values:
                        seen_values.add(value)
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
        code = self._session_code(item)
        title = self._session_title(item)
        abstract = self._session_abstract(item)
        topic = self._topic(attributes) or ""
        level = self._session_level(item, attributes)
        session_type = self._session_type(item, attributes)
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
        code = self._session_code(item)
        return {
            "id": self._session_identifier(item),
            "code": code,
            "title": self._session_title(item),
            "abstract": self._session_abstract(item),
            "type": self._session_type(item, attributes),
            "level": self._session_level(item, attributes),
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

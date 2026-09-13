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
    display_name = "AWS re:Invent Session Search"
    description = "Searches the public AWS re:Invent catalog and returns details for matching sessions."
    documentation: str = "https://github.com/iann0036/langflow-common-components"
    icon = "Amazon"
    name = "AWSReInventSessionSearch"

    CATALOG_PAGE_TEMPLATE = (
        "https://registration.awsevents.com/flow/awsevents/{event_identifier}/"
        "eventcatalog/page/eventcatalog"
    )
    SESSIONS_API = "https://catalog.awsevents.com/api/sessions"
    RF_API_PROFILE_ID = "mSEPBdEOSHwzxJwd7H8MfSWVylSYQsS4"
    RF_WIDGET_ID = "nbNFIlUhukEGI22KvPEwpPdWgK6FoPsi"
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
            info="The AWS event identifier used in the catalog page path.",
            value="reinvent2026",
            advanced=True,
        ),
        StrInput(
            name="browser_timezone",
            display_name="Browser Timezone",
            info="Timezone sent to the catalog API when retrieving sessions.",
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

    def _discover_profile_headers(self) -> dict[str, str]:
        return {
            "rfapiprofileid": self.RF_API_PROFILE_ID,
            "rfwidgetid": self.RF_WIDGET_ID,
        }

    def _fetch_page(self, profile_headers: dict[str, str], offset: int, size: int) -> tuple[list[dict], int | None]:
        headers = {
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "Origin": "https://registration.awsevents.com",
            "Referer": self._catalog_page_url(),
            "User-Agent": self.USER_AGENT,
            **profile_headers,
        }
        payload_data = {
            "type": "session",
            "browserTimezone": self.browser_timezone or "America/Los_Angeles",
            "catalogDisplay": "list",
            "from": str(offset),
            "size": str(size),
        }
        response = requests.post(
            self.SESSIONS_API,
            headers=headers,
            data=payload_data,
            timeout=60,
        )
        if response.status_code == 404:
            msg = "AWS re:Invent catalog sessions API was not available."
            raise RuntimeError(msg)
        response.raise_for_status()
        payload = response.json()
        if payload.get("responseCode") not in (None, "0", 0):
            msg = f"AWS re:Invent catalog API returned responseCode={payload.get('responseCode')}."
            raise RuntimeError(msg)

        if "sectionList" in payload and payload["sectionList"]:
            section = payload["sectionList"][0]
            return list(section.get("items", []) or []), section.get("total")
        if "items" in payload:
            return list(payload.get("items", []) or []), payload.get("total")

        msg = "Unexpected response from the AWS re:Invent catalog API."
        raise ValueError(msg)

    @staticmethod
    def _sort_matches(matches: list[dict[str, Any]]) -> None:
        matches.sort(key=lambda item: (-item["match_score"], item.get("code") or "", item.get("title") or ""))

    def _can_stop_early(self, query: str, matches: list[dict[str, Any]], max_results: int) -> bool:
        if not matches:
            return False

        normalized_query = self._normalize(query)
        top_match = matches[0]
        if self._normalize(top_match.get("code") or "") == normalized_query:
            return True
        if max_results == 1 and self._normalize(top_match.get("title") or "") == normalized_query:
            return True
        return False

    def _search_catalog_sessions(self, query: str, max_results: int) -> tuple[list[dict], int]:
        page_size = max(1, int(self.page_size or 100))
        profile_headers = self._discover_profile_headers()

        matches: list[dict] = []
        seen_ids: set[str] = set()
        offset = 0
        total: int | None = None
        scanned_sessions = 0

        while True:
            items, total = self._fetch_page(profile_headers, offset, page_size)
            if not items:
                break

            page_matches: list[dict[str, Any]] = []
            for item in items:
                session_id = str(
                    item.get("code")
                    or item.get("abbreviation")
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
            offset += page_size
            if self._can_stop_early(query, matches, max_results):
                return matches, scanned_sessions
            if total is not None and offset >= total:
                break

        return matches, scanned_sessions

    @staticmethod
    def _normalize(value: Any) -> str:
        return re.sub(r"\s+", " ", str(value or "").strip()).lower()

    @staticmethod
    def _attribute_map(item: dict) -> dict[str, list[str]]:
        attributes: dict[str, list[str]] = {}
        for attribute in item.get("attributevalues", []) or []:
            name = str(attribute.get("attribute") or "").strip()
            value = str(attribute.get("value") or "").strip()
            if name and value:
                attributes.setdefault(name, []).append(value)
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
        code = str(item.get("code") or item.get("abbreviation") or item.get("sessionID") or "")
        title = str(item.get("title") or "")
        abstract = str(item.get("abstract") or "")
        topic = self._topic(attributes) or ""
        level = " ".join(attributes.get("Level", []))
        session_type = str(item.get("type") or ", ".join(attributes.get("Type", [])) or "")
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
        code = str(item.get("code") or item.get("abbreviation") or item.get("sessionID") or "")
        return {
            "id": str(item.get("sessionID") or item.get("id") or code),
            "code": code,
            "title": item.get("title"),
            "abstract": item.get("abstract"),
            "type": item.get("type") or ", ".join(attributes.get("Type", [])),
            "level": ", ".join(attributes.get("Level", [])),
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

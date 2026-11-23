# { "Depends": "py-genlayer:1jb45aa8ynh2a9c9xn3b7qqh8sm5q93hwfp7jqmwsfhh8jpz09h6" }
from genlayer import *
import typing


class PublicEventCheck(gl.Contract):
    """
    PublicEventCheck - a public event verification primitive.

    Calendars, ticketing aggregators, travel planners and conference
    trackers all face the same question: is this event still
    happening, on the date and at the place it claims? Events are
    postponed, moved and cancelled all the time, and the old date
    keeps circulating long after the announcement changed. A stale
    listing is not a harmless error - people book flights and hotels
    around it.

    This contract attests an event against its own official page.
    The event name, the claimed date and location, and the official
    event page are fixed at submission time, and the verdict is
    taken by consensus against the live page. A fresh check is a
    fresh record: an event confirmed today can be rescheduled
    tomorrow, so a past verdict is never evidence about today.

    Consensus follows the structured-extraction pattern: the LLM
    only extracts a machine line, it never decides the outcome.

      STATUS|FOUND_DATE|FOUND_LOCATION

    STATUS is CONFIRMED, RESCHEDULED, CANCELLED or NOT_FOUND,
    FOUND_DATE is the date as shown on the page (YYYY-MM-DD, the
    start date for a multi-day event) and FOUND_LOCATION is the
    location as shown on the page. That line is judged under
    strict_eq, so validators must extract the same status, the
    same date and the same location.

    Every decision after that is deterministic code, and that is
    the point. A CONFIRMED verdict is only attested when the date
    found on the page equals the claimed date exactly, and the
    location found on the page matches the claimed location. A
    page that announces a new date therefore can never produce a
    false CONFIRMED: it ends in RESCHEDULED when the event is
    still happening on a different date, and in MISMATCH when
    the extraction does not line up with the claim at all.

    The location comparison is deliberately fail-closed. The
    extracted location must be present and non-empty: a CONFIRMED
    verdict is never attested on a missing location. The two
    locations are normalized (lowercase, punctuation removed,
    generic venue and function words dropped) and then compared
    as whole-token sets: every significant token of one must
    appear as a whole token of the other, and the token counts
    must agree. Substring overlap does not count ("York" inside
    "New York" is not a match), and a single shared word does
    not count ("Cambridge, Massachusetts" and "Cambridge,
    England" share a word but are different places, so they do
    not match). When the extracted location carries place tokens
    the claim never named, the contract refuses to confirm
    rather than guessing: the submitter should claim the full
    location.

    Two details of the extraction prompt matter. First, when a
    page has been rescheduled, its FAQ and history sections often
    still carry the old dates, so the prompt says to take the
    current announced dates, not any date mentioned elsewhere on
    the page. Second, multi-day events are compared on their
    start date only: a four-day event is one event, and its start
    date is the fact that has to match.
    """

    event_count: u256
    event_names: TreeMap[u256, str]
    claimed_dates: TreeMap[u256, str]
    claimed_locations: TreeMap[u256, str]
    event_pages: TreeMap[u256, str]
    statuses: TreeMap[u256, str]
    found_dates: TreeMap[u256, str]
    found_locations: TreeMap[u256, str]

    PENDING = "PENDING"
    CONFIRMED = "CONFIRMED"
    RESCHEDULED = "RESCHEDULED"
    CANCELLED = "CANCELLED"
    NOT_FOUND = "NOT_FOUND"
    MISMATCH = "MISMATCH"

    def __init__(self):
        self.event_count = u256(0)

    def _is_valid_date(self, date: str) -> bool:
        # Strict YYYY-MM-DD shape only; no calendar arithmetic.
        if len(date) != 10:
            return False
        if date[4] != "-" or date[7] != "-":
            return False
        for i in [0, 1, 2, 3, 5, 6, 8, 9]:
            if date[i] < "0" or date[i] > "9":
                return False
        return True

    def _normalized_location(self, location: str) -> str:
        # Normalize a location for comparison: lowercase, all
        # punctuation becomes a space, generic venue and function
        # words are dropped, and the remaining significant tokens
        # are joined with single spaces. "Le Centorial, Paris"
        # becomes "le centorial paris"; "The Royal Sonesta Hotel"
        # becomes "royal sonesta".
        lowered = location.lower()
        cleaned = ""
        for ch in lowered:
            if ("a" <= ch <= "z") or ("0" <= ch <= "9") or ch == " ":
                cleaned = cleaned + ch
            else:
                cleaned = cleaned + " "
        out = ""
        for word in cleaned.split(" "):
            if word == "" or len(word) < 2:
                continue
            if word == "the" or word == "and" or word == "of" or word == "at" or word == "in" or word == "on" or word == "for" or word == "no":
                continue
            if word == "hotel" or word == "centre" or word == "center" or word == "hall" or word == "theatre" or word == "theater" or word == "arena" or word == "stadium" or word == "campus" or word == "building" or word == "convention" or word == "exhibition" or word == "resort" or word == "lodge" or word == "inn" or word == "suite" or word == "suites" or word == "room" or word == "floor" or word == "street" or word == "road" or word == "avenue" or word == "ave" or word == "st" or word == "rd" or word == "blvd" or word == "drive" or word == "dr" or word == "lane" or word == "ln" or word == "court" or word == "ct" or word == "plaza" or word == "square" or word == "sq":
                continue
            out = out + word + " "
        return out.strip()

    def _location_matches(self, claimed: str, found: str) -> bool:
        # Robust normalized comparison. The extracted location
        # must be present and non-empty. Both sides are compared
        # as whole-token sets: same token count, and every token
        # of the claimed location must appear as a whole token of
        # the found location. Substring overlap ("York" in "New
        # York") and a single shared word ("Cambridge" in
        # "Cambridge, Massachusetts" vs "Cambridge, England")
        # never match. Extra place tokens on either side mean the
        # two are not the same place, so the comparison fails
        # closed instead of guessing.
        if found.strip() == "" or found.strip().upper() == "NONE":
            return False
        if claimed.strip() == "":
            return False
        c = self._normalized_location(claimed)
        f = self._normalized_location(found)
        if c == "" or f == "":
            return False
        if c == f:
            return True
        c_words = c.split(" ")
        f_words = f.split(" ")
        if len(c_words) != len(f_words):
            return False
        f_padded = " " + f + " "
        for word in c_words:
            if (" " + word + " ") not in f_padded:
                return False
        return True

    @gl.public.write
    def submit_event(
        self,
        event_name: str,
        claimed_date: str,
        claimed_location: str,
        event_page_url: str,
    ) -> int:
        event_name = event_name.strip()
        claimed_date = claimed_date.strip()
        claimed_location = claimed_location.strip()
        event_page_url = event_page_url.strip()

        assert len(event_name) >= 5, "event name too short"
        assert len(event_name) <= 200, "event name too long"
        assert self._is_valid_date(claimed_date), "claimed date must be YYYY-MM-DD"
        assert len(claimed_location) >= 3, "location too short"
        assert len(claimed_location) <= 200, "location too long"
        assert event_page_url.startswith("https://"), "event page must be https"
        assert len(event_page_url) <= 300, "event page URL too long"

        eid = self.event_count
        self.event_names[eid] = event_name
        self.claimed_dates[eid] = claimed_date
        self.claimed_locations[eid] = claimed_location
        self.event_pages[eid] = event_page_url
        self.statuses[eid] = self.PENDING
        self.found_dates[eid] = ""
        self.found_locations[eid] = ""
        self.event_count = eid + u256(1)
        return int(eid)

    @gl.public.write
    def resolve_event(self, event_id: int) -> str:
        eid = u256(event_id)
        assert eid in self.statuses, "unknown event"
        assert self.statuses[eid] == self.PENDING, "event already resolved"

        # Copy storage into locals: non-deterministic blocks may not
        # touch contract storage, they may only capture local values.
        event_name = self.event_names[eid]
        claimed_date = self.claimed_dates[eid]
        claimed_location = self.claimed_locations[eid]
        event_page_url = self.event_pages[eid]

        def extract_event() -> str:
            page = gl.nondet.web.render(event_page_url, mode="text")
            prompt = f"""Check one public event using only the official page below.

Event: {event_name}
Claimed date: {claimed_date}
Claimed location: {claimed_location}

Page content:
{page[:4000]}

Reply with exactly one line, nothing else, in this format:
STATUS|FOUND_DATE|FOUND_LOCATION

STATUS is one of:
CONFIRMED - the event is happening on the claimed date at the claimed location
RESCHEDULED - the event is still happening, but on a different date or at a different location
CANCELLED - the page says the event is cancelled
NOT_FOUND - the page does not exist, was removed, or shows no such event

FOUND_DATE is the event date as currently announced on the page, in YYYY-MM-DD format. For a multi-day event, use the start date only. Take the current announced dates, not dates mentioned in FAQ, history, or past-edition sections of the page. If the event is cancelled or not found, write NONE.
FOUND_LOCATION is the location as currently announced on the page. If the event is cancelled or not found, write NONE."""
            return gl.nondet.exec_prompt(prompt).strip()

        line = gl.eq_principle.strict_eq(extract_event)

        # Deterministic parsing and decision. The LLM extracted
        # data; it never decided the outcome.
        first_sep = line.find("|")
        if first_sep == -1:
            self.statuses[eid] = self.MISMATCH
            return self.MISMATCH
        rest = line[first_sep + 1:]
        second_rel = rest.find("|")
        if second_rel == -1:
            self.statuses[eid] = self.MISMATCH
            return self.MISMATCH

        status_word = line[:first_sep].strip().upper()
        found_date = rest[:second_rel].strip()
        found_location = rest[second_rel + 1:].strip()
        self.found_dates[eid] = found_date
        self.found_locations[eid] = found_location

        if status_word == "NOT_FOUND":
            final = self.NOT_FOUND
        elif status_word == "CANCELLED":
            final = self.CANCELLED
        elif status_word == "RESCHEDULED":
            if found_date != "" and found_date != "NONE" and found_date != claimed_date:
                final = self.RESCHEDULED
            elif found_location != "" and found_location != "NONE" and not self._location_matches(claimed_location, found_location):
                final = self.RESCHEDULED
            else:
                final = self.MISMATCH
        elif status_word == "CONFIRMED":
            # Confirmation requires a present, non-empty extracted
            # location as well as an exact date and a robust
            # normalized location match. A missing location can
            # never confirm.
            location_present = found_location != "" and found_location.upper() != "NONE"
            if found_date == claimed_date and location_present and self._location_matches(claimed_location, found_location):
                final = self.CONFIRMED
            else:
                final = self.MISMATCH
        else:
            final = self.MISMATCH

        self.statuses[eid] = final
        return final

    @gl.public.view
    def get_event(self, event_id: int) -> typing.Any:
        eid = u256(event_id)
        assert eid in self.statuses, "unknown event"
        return {
            "id": event_id,
            "event": self.event_names[eid],
            "claimed_date": self.claimed_dates[eid],
            "claimed_location": self.claimed_locations[eid],
            "event_page": self.event_pages[eid],
            "status": self.statuses[eid],
            "found_date": self.found_dates[eid],
            "found_location": self.found_locations[eid],
        }

    @gl.public.view
    def get_status(self, event_id: int) -> str:
        eid = u256(event_id)
        assert eid in self.statuses, "unknown event"
        return self.statuses[eid]

    @gl.public.view
    def is_confirmed(self, event_id: int) -> bool:
        eid = u256(event_id)
        assert eid in self.statuses, "unknown event"
        return self.statuses[eid] == self.CONFIRMED

    @gl.public.view
    def get_event_count(self) -> int:
        return int(self.event_count)

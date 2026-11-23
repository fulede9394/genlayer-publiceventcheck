# PublicEventCheck — Public Event Verification Primitive

A standalone Intelligent Contract that attests whether a public
event is still happening, on the date and at the place it claims,
against the event's own official page.

## Deployed

- Network: StudioNet (GenLayer Studio)
- Contract: `0xD5ff5313f0DdCc216631ffE5be66Bd3538a64dE7`
- Deploy tx: `0xd8b80230b05699e7810f5b008c2d2fb9656c270de40986dafcff4d518049f36b`
- Explorer: https://explorer-studio.genlayer.com/address/0xD5ff5313f0DdCc216631ffE5be66Bd3538a64dE7
- Studio: https://studio.genlayer.com/?import-contract=0xD5ff5313f0DdCc216631ffE5be66Bd3538a64dE7

## Why this exists

Calendars, ticketing aggregators, travel planners and conference
trackers all face the same question: is this event still happening,
on the date and at the place it claims? Events are postponed, moved
and cancelled all the time, and the old date keeps circulating long
after the announcement changed. A stale listing is not a harmless
error — people book flights and hotels around it. PublicEventCheck
turns "is this event still on?" into a reusable primitive with a
visible audit trail.

1. `submit_event(event_name, claimed_date, claimed_location, event_page_url)` —
   the event, the claimed date and location, and the official page
   are fixed at submission time.
2. `resolve_event(event_id)` — the LLM only extracts a machine
   line, `STATUS|FOUND_DATE|FOUND_LOCATION`, judged under strict
   equality.
3. Every decision after that is deterministic code. A CONFIRMED
   verdict is only attested when the date found on the page equals
   the claimed date exactly, and the location found on the page
   matches the claimed location.

## Location comparison

Confirmation requires a present, non-empty extracted location:
a CONFIRMED verdict is never attested on a missing location.
The two locations are normalized first (lowercase, punctuation
removed, generic venue and function words such as "hotel",
"centre" or "hall" dropped) and then compared as whole-token
sets: the token counts must agree, and every significant token
of one side must appear as a whole token of the other. Substring
overlap does not count — "York" inside "New York" is not a
match — and a single shared word does not count either:
"Cambridge, Massachusetts" and "Cambridge, England" share a
word but are different places, so they do not match. When the
extracted location carries place tokens the claim never named,
the contract fails closed to MISMATCH instead of guessing; the
submitter should claim the full location. The extraction prompt
asks for the venue name and the city only — no street address,
postcode or country, and never a city alone — so that the
extracted location is stable enough for this comparison to
judge. Extraction can still vary run to run, which is a known
residual risk of that step, not of the comparison: the
comparison can only judge what was extracted, and it fails
closed whenever the extraction is complete.

## The reschedule trap

When a page has been rescheduled, its FAQ and history sections
often still carry the old dates. The extraction prompt therefore
says to take the current announced dates, not any date mentioned
elsewhere on the page, and multi-day events are compared on their
start date only. A page that announces a new date can never
produce a false CONFIRMED: it ends in RESCHEDULED when the event
is still happening on a different date, and in MISMATCH when the
extraction does not line up with the claim at all.

## State design

One-way state machine per event:
`PENDING -> CONFIRMED | RESCHEDULED | CANCELLED | NOT_FOUND | MISMATCH`

- `CONFIRMED`: the event is happening on the claimed date at the
  claimed location.
- `RESCHEDULED`: the event is still happening, but on a different
  date or at a different location.
- `CANCELLED`: the page says the event is cancelled.
- `NOT_FOUND`: the page does not exist, was removed, or shows no
  such event.
- `MISMATCH`: the extraction does not line up with the claim —
  for example the page says CONFIRMED but the date or location
  found does not match, or it says RESCHEDULED without a new
  date. Treat as "do not act on this event".

Because `found_date` and `found_location` are stored, anyone can
see *what* the page actually announced, instead of getting a
single opaque verdict.

## Try it in GenLayer Studio

1. Paste `contracts/public_event_check.py` into Studio and deploy (no args).
2. `submit_event` with, for example:
   - event_name: `ERCC Annual General Meeting and Conference 2026`
   - claimed_date: `2026-12-01`
   - claimed_location: `Le Centorial, Paris`
   - event_page_url: `https://www.icmagroup.org/events/ercc-annual-general-meeting-and-conference-2026/`
3. `resolve_event(0)`, then `get_event(0)` — expect `CONFIRMED`
   with `found_date` `2026-12-01` and a matching location.

## Tests

See `tests/test_cases.md` (12 cases): input validation, unknown /
double resolution, the date and location gates, and all five
terminal states.

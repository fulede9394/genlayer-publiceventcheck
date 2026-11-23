# PublicEventCheck — test cases

Run manually in GenLayer Studio after deploying
`contracts/public_event_check.py` (no constructor args).

## Deterministic validation

1. `submit_event` with an event name shorter than 5 characters —
   expect rejection ("event name too short").
2. `submit_event` with a claimed date that is not `YYYY-MM-DD`
   (for example `1 December 2026`) — expect rejection
   ("claimed date must be YYYY-MM-DD").
3. `submit_event` with an `http://` (non-https) event page URL —
   expect rejection ("event page must be https").
4. `submit_event("ERCC Annual General Meeting and Conference 2026", "2026-12-01", "Le Centorial, Paris", "https://www.icmagroup.org/events/ercc-annual-general-meeting-and-conference-2026/")` — expect
   event id `0`, and `get_event_count()` returns `1`.
5. `get_status(99)` on an unknown event — expect rejection
   ("unknown event").
6. `resolve_event(99)` on an unknown event — expect rejection
   ("unknown event").

## Non-deterministic verdict paths

7. Resolve the ICMA ERCC 2026 event from case 4 — expect
   `CONFIRMED`, with `found_date` `2026-12-01` and a matching
   location, and `is_confirmed(0)` returns `true`.
8. Submit the NICE K12 Cybersecurity Education Conference with the
   old claim — event name
   `NICE K12 Cybersecurity Education Conference`, claimed date
   `2026-12-07`, location `New Orleans`, page
   `https://www.k12cybersecurityconference.org/faqs` — and resolve
   it. The conference was rescheduled from December 7–8, 2026 to
   March 7–9, 2027 at the Royal Sonesta New Orleans. Expect
   `RESCHEDULED`, with `found_date` `2027-03-07`.
   Note: the FII10 case was retired from this list — both
   fii-institute.org pages return HTTP 403 to GenLayer's web
   fetcher, so no extraction ever runs and the event stays
   PENDING. That is a property of the FII site, not of the
   contract: the same RESCHEDULED path is covered by the NICE
   K12 case above.
9. Submit the Harvard Asia Center event — event name
   `Global Confucius Symposium and Ritual`, claimed date
   `2026-10-16`, location `Cambridge`, page
   `https://asiacenter.harvard.edu/announcements/event-cancellation-announcement-global-confucius-symposium-and-ritual`
   — and resolve it. Expect `CANCELLED`.
10. Resolve an already-resolved event a second time — expect
    rejection ("event already resolved"). A CONFIRMED event that
    is later rescheduled stays CONFIRMED in its own record;
    submit a new event for a fresh check.
11. Submit the ICMA ERCC 2026 event again, same date and page as
    case 4, but with a wrong claimed location — `Le Centorial,
    London` — and resolve it. The page still says the event is
    happening, at "Le Centorial, Paris", so the location has
    changed, not vanished: expect `RESCHEDULED`. The key
    assertion is that it must NOT be `CONFIRMED` — a shared
    venue name alone must not confirm a different city.
12. Submit the ICMA ERCC 2026 event again, same date and page,
    but with an underspecified claimed location — `Paris` — and
    resolve it. The extraction prompt asks for venue and city,
    so the extracted location should be "Le Centorial, Paris",
    which carries place tokens ("le", "centorial") the claim
    never named, so the comparison fails closed: expect
    `MISMATCH`. The claim should name the full location.
    Note: the extraction itself can vary run to run (one run
    returned only "Paris", which then matched and confirmed).
    That variance is a known residual risk of the extraction
    step, not of the comparison: the comparison can only judge
    what was extracted, and it fails closed whenever the
    extraction is complete.

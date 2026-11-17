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
8. Submit FII10 with the old claim — event name `FII10`, claimed
   date `2026-10-26`, location `Riyadh`, page
   `https://fii-institute.org/conference/fii-10th-edition/` — and
   resolve it. The page's FAQ still carries the old October 2026
   dates, so the extraction must take the current announced dates.
   Expect `RESCHEDULED`, with `found_date` `2027-10-25`. If the
   extraction is unstable on this page, the fallback case is the
   press release at
   `https://fii-institute.org/press/fii-institute-announces-new-dates-for-fii10-october-25-28-2027/`.
9. Submit the Harvard Asia Center event — event name
   `Global Confucius Symposium and Ritual`, claimed date
   `2026-10-16`, location `Cambridge`, page
   `https://asiacenter.harvard.edu/announcements/event-cancellation-announcement-global-confucius-symposium-and-ritual`
   — and resolve it. Expect `CANCELLED`.
10. Resolve an already-resolved event a second time — expect
    rejection ("event already resolved"). A CONFIRMED event that
    is later rescheduled stays CONFIRMED in its own record;
    submit a new event for a fresh check.

# DESIGN: JB-82 feedback + usage events (first observability slice)
_v1 · 2026-10-11 · Labels: ✅ verified · ⚠️ inferred · ❓ unchecked_
_BT's order (2026-10-11): design first, observability after. The design pass (#181 children) is merged, so this is the first slice._

## Problem
- ✅ No analytics have ever recorded: `attsis.goatcounter.com` → HTTP 400 (the site isn't created; BT must sign up).
- ✅ No way for a visitor to say "good match / bad match / something's broken".
- The growth plan's gates (`GROWTH_INVESTMENT_PLAN.md`) need *setups completed*, *map used*, *👍/👎* and *job clicks*.

## Decisions
### D1. Where events go
| Option | Pros | Cons |
|---|---|---|
| **A. GoatCounter custom events** (already on the page) | Free tier, no cookies, no backend, same dashboard as pageviews | Counts only (no per-user funnels); nothing until BT creates the site |
| B. Own endpoint (e.g. Cloudflare Worker + KV) | Full control, per-event fields | A backend to run, plus privacy/ToS work |
| C. Google Analytics | Rich | Cookies + consent banner; against the privacy promise on the page |

**Choice: A.** Events are no-ops until GoatCounter is live, and they never send CV contents.

### D2. Event names (paths)
| Path | When | Payload |
|---|---|---|
| `setup/quickstart`, `setup/profile` | Save on the Welcome card / keyword editor | none |
| `map/used` | First switch to List + map or Map in a session | none |
| `click/<company>` | "Open posting" or title link | company name only (public data) |
| `vote/up/<company>`, `vote/down/<company>` | 👍 / 👎 in an expanded card | company name only |

Company names are public posting data, not personal data. **No CV text, skills, name or home are ever sent.**

### D3. Votes
In the expanded card: **"Good match? 👍 👎"**. Stored per browser (`jobboard_votes`) so the choice shows on return. **Tradeoff:** votes don't change the score yet. They're a signal for tuning the scorer (#197) once there's enough data.

### D4. Report a problem
A footer link opens a **prefilled GitHub issue** (title "Problem report", page URL in the body, label `type:bug`). **Tradeoff:** it needs a GitHub account. **Why not mailto:** it would publish BT's address and email links are unreliable. **Later:** a form when there's a backend.

## Acceptance
- [ ] `track()` is a safe no-op when GoatCounter hasn't loaded.
- [ ] The events in D2 fire at the right moments (verified by stubbing `window.goatcounter.count` in a browser test).
- [ ] Votes persist across reload; clicking a vote doesn't collapse the card.
- [ ] Footer link opens a new GitHub issue with a prefilled title.
- [ ] pytest + smoke + preprod smoke.

## BT action
Create the GoatCounter account + site `attsis` (≈ 15 min ⚠️). Until then every event is silently dropped.

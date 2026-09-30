# Free LLM APIs — Landscape & Fallback Options

**Purpose:** Reference of free-tier LLM providers usable as fallbacks when Claude tokens are exhausted or as tier-2 layers behind primary inference (currently Groq).
**Last reviewed:** 2026-09-28
**Owner:** attsis-jobboard research notes

---

## TL;DR

- **Claude Code CLI cannot be swapped to a free proxy** — it authenticates against Anthropic. Only `GitHub Models` actually serves Claude on a free-ish tier, but not through the CLI.
- **For app-level LLM calls** (content generation, scoring, extraction), stacking free tiers is viable. Groq is primary; Gemini 2.5 Flash is the strongest secondary.
- Free tiers are **not** production substrates — rate limits shift, ToS forbid resale, no SLA.

---

## Practical Providers

| Provider | Best Model | Free Limit | Signup | Notes |
|---|---|---|---|---|
| **Groq** | Llama 3.3 70B, gpt-oss-120b | 30 RPM / 250 RPD | Email | Already in attsis pipeline; fastest inference |
| **Google Gemini** | 2.5 Flash | 15 RPM / 1,500 RPD, 1M context | Email | Best free tier overall; multimodal |
| **Cerebras** | Llama 3.3 70B | generous | Email | Ultra-fast, comparable to Groq |
| **Mistral AI** | Mistral Large, Codestral | free mode | No card | Solid EU option |
| **OpenRouter** | 34 free models | 50 RPD (1,000 with $10 topup) | Email | Meta-router — one key, many models |
| **NVIDIA NIM** | 132 models | 40 RPM | Phone verify | Widest catalogue |
| **SambaNova** | Llama variants | 200K tokens/day | Email | Fast |
| **Cloudflare Workers AI** | Llama, Mistral | 10K neurons/day | Email | Edge-native |
| **GitHub Models** | GPT-4o, Claude, Llama | Rate-limited | GitHub | Only free-ish source of Claude models |
| **DeepSeek** | V3, R1 | dynamic | Registration | Strong reasoning |
| **Cohere** | Command R+ | 1,000 calls/month | Email | Non-commercial only |
| **xAI** | Grok 3 | Credit-based | Registration | Requires topup for meaningful use |
| **Hugging Face** | 8 hosted | Credit-metered | Email | Best for open-source models |
| **LLM7.io** | 20 | 10 RPM, 60/hr | No | Aggregator |

## Aggregators / Meta-gateways

- **freellmapi** (OliverMoooi/freellmapi) — OpenAI-compatible `/v1` proxy stacking 34 providers, 635 endpoints, ~7.4B tokens/month. Explicitly labelled *personal experimentation only*.
- **OpenRouter** — commercial-grade router with free tier; safer than raw freellmapi for anything real.

---

## Recommendations for Global Attsis

1. **Keep Groq as primary** — already wired via urllib with custom User-Agent (Cloudflare workaround, see attsis-shorts memory).
2. **Add Gemini 2.5 Flash as tier-2** — different provider, disjoint rate limits, 1,500 RPD is generous for daily-shorts scale.
3. **Reserve OpenRouter as tier-3** — one key, auto-routes across free models if both above fail.
4. **Do NOT** point production code at freellmapi — README states personal-experimentation only.
5. **For Claude Code specifically** — no free replacement exists via the CLI. Fallback path is switching model with `/model` inside Claude Code (Haiku 4.5 is cheapest) rather than swapping vendors.

---

## Sources

- [OpenRouter: 13 free LLM APIs compared (2026)](https://openrouter.ai/blog/tutorials/free-llm-apis-compared/)
- [KDnuggets: 5 Free LLM API Providers 2026](https://www.kdnuggets.com/5-free-llm-api-providers-you-can-use-in-2026)
- [freellmpool provider list](https://0xzr.github.io/freellmpool/free-llm-api-providers-list.html)
- [awesome-freellm-apis](https://github.com/open-free-llm-api/awesome-freellm-apis)
- [OliverMoooi/freellmapi (original repo)](https://github.com/OliverMoooi/freellmapi)

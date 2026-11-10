# 3–5 minute video: actual execution checklist + narration outline

**Do not record pretend executions. Replace bracketed text with observations from your real deployment.**

**0:00–0:25 Intro:** "I'm demonstrating SecureCloud AI, a five-page website deployed on AWS with four specialized agents for cloud requirements, infrastructure, security and verification." Open live custom HTTPS URL.

**0:25–1:00 Website:** Navigate Home, About, Architecture, Security, Contact. Resize browser. Click deployment checklist on Home; submit demo contact form to show the JS response.

**1:00–1:55 AWS security:** AWS Console: show private S3 and block-public-access; demonstrate anonymous direct S3 object URL is denied. Show CloudFront with OAC, ACM certificate status, Route 53 alias record. In browser or terminal show HTTP redirects to HTTPS. Blur/avoid secrets.

**1:55–2:55 Agent run:** Show agents/core.py role definitions, run_agents.py orchestration, and agents/tools.py. Execute `python run_agents.py --live --aws-audit` live. Show generated requirements.json, infrastructure.json, security.json, verification.json, and logs/execution.jsonl. Explain model decisions versus Python-invoked tools; show exact evidence of two executable tools.

**2:55–4:15 Recovery:** Show the disposable recovery-probe workflow; it does not touch website pages. Run `python -m scripts.failure_experiment seed --approve` and `verify`, then `python -m scripts.failure_experiment break --approve` and `verify`. Run `python run_agents.py --live --recovery-probe` to show the verification agent's diagnosis from the observed missing probe. Restore with `python -m scripts.failure_experiment restore --approve`, verify it, and rerun the agent. After recording the successful recovery evidence, remove the disposable probe with `python -m scripts.failure_experiment cleanup --approve`. Capture actual chronological logs. If recovery cannot be demonstrated, say so; do not fake it.

**4:15–4:40 Close:** Explain one actual challenge and the value of human approval, structured JSON, and independent verification.

**Before recording:** browser zoom readable, credentials hidden, terminal showing correct directory, internet connected, all page URLs verified, AWS console logged in, correct project bucket.

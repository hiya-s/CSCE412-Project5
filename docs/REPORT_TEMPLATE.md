# SecureCloud AI: Multi-Agent AWS Website Deployment and Verification

**Author:** [Student name]  
**Course:** CSCE 412  
**Website:** [LIVE HTTPS URL AFTER VERIFICATION]  
**Private repository:** [URL, TA/instructor granted access]  
**Date:** [date]

> Completion status: DRAFT. Replace every bracketed field with actual evidence. Do not claim AWS operations, model API calls or failure experiments were performed until real evidence exists.

## 1. Project Overview and Website Design

SecureCloud AI is an educational five-page responsive website illustrating how a structured multi-agent workflow can support secure AWS cloud operations. It contains Home, About, Architecture, Security and Contact pages. Navigation is via standard HTML links. The JavaScript contact form displays an in-browser acknowledgement without transmitting a message, and the home page has an interactive checklist.

**Evidence:** [Screenshots of the actual five pages, mobile and desktop; live URL].

## 2. AWS Infrastructure Architecture

```text
Browser -> Route 53 custom DNS -> CloudFront (HTTPS redirect; ACM TLS certificate)
                                   |
                                   +-- OAC signed requests -> private S3 bucket
```

Route 53 maps the custom domain to the CloudFront distribution. ACM issues a DNS-validated TLS certificate in us-east-1. CloudFront handles HTTPS and caching. OAC signs access to a private S3 origin; the S3 bucket policy permits `s3:GetObject` only to the configured CloudFront distribution service principal. Terraform manages these resources and a separately approved sync tool publishes website files.

**Evidence:** [Terraform apply output, console screenshots, exact region, distribution ID redacted as appropriate, curl tests].

## 3. AI Agent Architecture

```text
User request
  |-- Requirements Agent -> requirements.json
  |-- Infrastructure Agent (reads requirements) -> infrastructure.json
  |-- Security Agent (reads requirements and infrastructure) -> security.json
  |-- deterministic local / HTTP / AWS read-only tools -> observations
  `-- Verification Agent (reads upstream decisions + observed tools) -> verification.json
```

Agents use the [actual model name/provider] through the OpenAI-compatible Python SDK as configured. The orchestrator calls the LLM with specialized system instructions, requests JSON, validates the keys and types, writes outputs and passes Python dictionaries to downstream agents. Unlike a fully autonomous tool-calling framework, this workflow uses Python-controlled tool selection. LLM decisions are recommendations; tools perform concrete checking and explicitly approved cloud modifications.

**Evidence:** [Real logs with timestamps and filenames, actual model used, representative JSON].

## 4. Agent Implementation and Execution

`run_agents.py` invokes each role and passes validated JSON to the next agent. `check_local_site()` verifies expected website files and linked local targets. `check_http_site()` performs actual network requests to all five deployed pages and checks response status and final HTTPS scheme. `aws_readonly_audit()` optionally queries real AWS resource configuration. `scripts.publish_site` requires `--approve` for S3 sync and CloudFront invalidation. Structured events are logged as JSONL.

**Examples from actual execution:** [Agent input], [model output], [tool args and tool results], [validation outcome], [approval record].

## 5. Security Implementation

S3 Block Public Access is configured on the website bucket, with a CloudFront-only bucket policy. CloudFront Origin Access Control signs origin requests. ACM validates the domain through a Route 53 DNS record. CloudFront redirects HTTP requests to HTTPS. Secrets stay outside Git through `.env` and the standard AWS credentials chain. AWS permissions should be scoped to the project resources and actions required.

**Evidence:** [S3 access-block screenshot, OAC setup, certificate status, Route 53 alias, successful HTTPS, denied anonymous direct S3 access, redacted IAM permissions].

## 6. Failure Detection and Recovery

A controlled experiment removes `about.html` from the website bucket after explicit approval, requests CloudFront cache invalidation, and observes a failed `/about.html` HTTP request. The verifier consumes the observation and proposes recovery. The operator restores the locally saved `about.html` to S3, invalidates the path and verifies HTTP success. The mutation and HTTP checker are logged.

**Only complete this section after running the real experiment.** Record actual times, failure status, agent diagnosis, approved action, recovery tool response, final HTTP status, and supporting screenshots/log fragments. [Real evidence here].

## 7. Challenges, Lessons Learned and References

**Actual challenge and resolution:** [e.g., certificate validation, IAM permissions, CDN caching; describe what you observed and fixed].

**Lessons:** Separate AI recommendations from deterministic operations. Validate structure and observe real state before claiming deployment success. Require explicit human approval for consequential cloud actions.

**References:** [AWS S3 security, CloudFront OAC, ACM DNS validation, Route 53, OpenAI API documentation, NIST guidance if used].

**AI disclosure:** [List any actual AI systems used and what they did; student reviewed/tests performed].

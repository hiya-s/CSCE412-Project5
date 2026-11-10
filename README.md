# CSCE 412 Project 5 — SecureCloud AI

**Status:** starter implementation. Website and local Python tools can be tested immediately. AWS deployment, model calls, and failure recovery **have not been executed** in this supplied archive. Do not claim they have.

## Deliverables implemented

- Five responsive linked website pages (`website/`) and interactive client-side JavaScript demo.
- Four distinct LLM agents: requirements, infrastructure, security, verification/recovery.
- Validated structured JSON and logged file-based agent-to-agent communication (`outputs/` created on execution).
- Two meaningful deterministic tools: local website checking, live HTTPS checks. Optional read-only AWS security audit. All actual calls recorded in `logs/execution.jsonl`.
- Human-approved S3 sync/CloudFront invalidation tools and controlled reversible AWS failure experiment.
- Terraform infrastructure: private S3, CloudFront OAC, ACM certificate in us-east-1, Route53 A/AAAA alias, HTTPS redirect.
- Report and video outline templates in `docs/` (must fill with real results).

## 1. Set up local Python

Requires Python 3.10+, an actual LLM API key, and network access. AWS operations also require AWS CLI configured with appropriately scoped credentials; Terraform is needed for infrastructure deployment.

```bash
cd csce412-project5
python -m venv .venv
source .venv/bin/activate               # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env                    # Windows: copy .env.example .env
# Edit .env to insert the LLM key; keep .env private.
python -m unittest discover -s tests -v
python run_agents.py
```

Review `outputs/*.json` and `logs/execution.jsonl` from the **real** execution. API usage may incur charges. The model uses `OPENAI_MODEL` (default `gpt-4.1-mini`; choose a model available to your API account).

`run_agents.py` uses the LLM to produce distinct decisions, passes the outputs along to subsequent agents and executes local tooling. It does not autonomously choose tools: the Python workflow invokes allowlisted tools deterministically. This is an **orchestrated multi-agent system**, not a fully autonomous tool-calling agent.

## 2. Deploy AWS hosting (requires domain and AWS account)

**Prerequisites:** a domain whose authoritative DNS is hosted in an *existing public Route 53 hosted zone*, AWS credentials with necessary rights, AWS CLI and Terraform installed. Check billing and domain ownership before continuing; CloudFront, Route 53, domain registration, and other services can incur charges. Use only your own account.

```bash
cp infra/terraform.tfvars.example infra/terraform.tfvars
# Edit domain_name, hosted_zone_name and a globally unique bucket_name.
cd infra
terraform init
terraform fmt -check
terraform validate
terraform plan
# Review the plan and actual costs before human approval:
terraform apply
terraform output
cd ..
```

ACM DNS validation and CloudFront deployment can take time. Do not submit a URL until it actually works. Update `.env` with the output `website_url`, `bucket_name`, and `distribution_id`.

```bash
python -m scripts.publish_site             # dry run only
python -m scripts.publish_site --approve   # real website S3 sync + invalidation
python run_agents.py --live --aws-audit    # real observed output, requires API and AWS credentials
```

Verify all five pages and HTTPS. Verify that direct anonymous S3 object access is denied. Confirm AWS console: S3 public-access block, CloudFront OAC, ACM certificate status, Route53 zone aliases. Keep screenshots with secrets cropped.

## 3. Controlled failure and recovery (real AWS changes)

ONLY perform when website deployment is confirmed and you own the bucket. `break` deliberately deletes the single `about.html` object (recoverable from the local website directory). Running any change requires `--approve`. DO NOT run on production or shared buckets.

```bash
python -m scripts.failure_experiment break --approve
# Wait for CloudFront invalidation to complete.
python -m scripts.failure_experiment verify  # observe about.html failing
python run_agents.py --live                  # agents analyze observed failure
python -m scripts.failure_experiment restore --approve
# Wait for CloudFront invalidation to complete.
python -m scripts.failure_experiment verify  # verify five pages restored
python run_agents.py --live                  # capture actual diagnosis/verification
```

**Important:** The HTTP checker currently reports every failing page, but CloudFront may return a `403` or `404` when the object is missing. If about.html is still cached, wait until the invalidation completes. Keep logs and screenshots of actual AWS state, failed requests and recovery. The failure experiment's AWS calls are logged. The security and verification agents suggest changes; they do NOT autonomously deploy.

## 4. Submission mapping

| Canvas item | What to submit |
| --- | --- |
| Domain link | Live custom HTTPS URL, after checking in an incognito browser |
| Documentation PDF | Fill `docs/REPORT_TEMPLATE.md` with real data, diagrams/screenshots and export to PDF |
| Video | Record actual console + agent workflow using `docs/DEMO_SCRIPT.md` |
| Execution log ZIP | After real runs, package `logs/execution.jsonl`, `outputs/*.json`, and a README describing sequence |
| GitHub | Push source to a **private** repository, grant instructor/TA access, submit URL |

Do **not** add `.env`, Terraform state, private credentials, or sensitive log data to Git. Carefully review logs before sharing; user prompts and AWS identifiers may appear. The only valid logs are from real invocations; none are supplied as invented successes.

## 5. What needs your input

- Your registered domain and Route 53 public hosted zone.
- A configured AWS account / credentials.
- An API key for an available model.
- Actual deployed site URL, GitHub URL, proof and screenshots for the report.

## Design safety notes and limitations

- CloudFront's OAC and bucket policy restrict ordinary anonymous S3 access. An IAM principal with other permissions can still access S3; use least privilege.
- The local tool checks presence of files, not all possible HTML correctness issues.
- HTTPS HTTP checks validate responses but are not a complete certificate/security audit.
- The AWS read-only audit provides observations; missing permissions are logged as errors, never silently treated as success.
- The recovery demo intentionally mutates one S3 object under explicit approval. Always restore it.
- Terraform `apply` requires human review; never execute it using unvalidated LLM-generated shell commands.

"""Real multi-agent workflow, with structured file exchange and observable tools."""
import argparse
import json
import os
from pathlib import Path
from dotenv import load_dotenv
from agents.core import ROOT, record, run_agent, write_json
from agents.tools import check_local_site, check_http_site, aws_readonly_audit


def main():
    load_dotenv(ROOT / '.env')
    parser = argparse.ArgumentParser()
    parser.add_argument('--request', default='Build a five-page responsive educational cloud-security website with a contact form demonstration, custom HTTPS domain, private S3, CloudFront, ACM, and Route 53.')
    parser.add_argument('--live', action='store_true', help='Verify deployed website via HTTP')
    parser.add_argument('--aws-audit', action='store_true', help='Read AWS config using configured credentials')
    args = parser.parse_args()
    try:
        requirements = run_agent('requirements', {'user_request': args.request})
        infrastructure = run_agent('infrastructure', {'requirements': requirements})
        security = run_agent('security', {'requirements': requirements, 'infrastructure': infrastructure})
        local = check_local_site()
        observations = {'local_site': local}
        if args.live:
            observations['http_site'] = check_http_site(os.environ['SITE_URL'])
        if args.aws_audit:
            observations['aws_security'] = aws_readonly_audit(os.environ['S3_BUCKET'], os.environ['CLOUDFRONT_DISTRIBUTION_ID'])
        verification = run_agent('verification', {'requirements': requirements, 'security_review': security, 'observed_tool_results': observations})
        workflow = {'requirements': requirements, 'infrastructure': infrastructure, 'security': security, 'observations': observations, 'verification': verification}
        write_json('agent_communication.json', workflow)
        record('workflow_finished', local_check_passed=local['ok'], live_verification_requested=args.live,
               deployment_performed=False, success_is_not_implied=True)
        print('\nAgent results saved to outputs/; authentic chronological logs saved to logs/execution.jsonl')
    except Exception as e:
        record('workflow_failed', error=str(e))
        raise


if __name__ == '__main__':
    main()

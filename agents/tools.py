"""Approved deterministic tools. Model text is NEVER executed as shell commands."""
import os
import subprocess
from pathlib import Path
from urllib.parse import urlparse
import requests
from agents.core import ROOT, record

ALLOWED_FILES = {'index.html', 'about.html', 'projects.html', 'security.html', 'contact.html', 'style.css', 'app.js'}


def check_local_site() -> dict:
    site = ROOT / 'website'
    missing = sorted(x for x in ALLOWED_FILES if not (site / x).is_file())
    broken_links = []
    for html in site.glob('*.html'):
        text = html.read_text(encoding='utf-8')
        for target in [x for x in ALLOWED_FILES if x.endswith('.html')]:
            if f'href="{target}"' in text and not (site / target).exists():
                broken_links.append(f'{html.name}: {target}')
    result = {'ok': not missing and not broken_links, 'missing': missing, 'broken_links': broken_links}
    record('tool_result', tool='check_local_site', result=result)
    return result


def check_http_site(site_url: str) -> dict:
    parsed = urlparse(site_url)
    if parsed.scheme not in ('https', 'http') or not parsed.netloc or parsed.username or parsed.password:
        raise ValueError('Set a valid website URL')
    results = []
    # User-controlled URL; use only your own website, not internal/private endpoints.
    for page in ('', 'about.html', 'projects.html', 'security.html', 'contact.html'):
        url = site_url.rstrip('/') + '/' + page
        try:
            response = requests.get(url, timeout=12, allow_redirects=True)
            results.append({'url': url, 'status': response.status_code,
                            'https_final': response.url.startswith('https://'),
                            'ok': response.ok and response.url.startswith('https://')})
        except requests.RequestException as e:
            results.append({'url': url, 'ok': False, 'error': str(e)})
    output = {'ok': all(x['ok'] for x in results), 'pages': results}
    record('tool_result', tool='check_http_site', result=output)
    return output


def aws_readonly_audit(bucket: str, distribution_id: str) -> dict:
    """Read-only AWS observations; credentials come from normal AWS credential chain."""
    import boto3
    s3 = boto3.client('s3')
    cf = boto3.client('cloudfront')
    observations = {}
    try:
        observations['public_access_block'] = s3.get_public_access_block(Bucket=bucket)['PublicAccessBlockConfiguration']
    except Exception as e:
        observations['public_access_block_error'] = str(e)
    try:
        dist = cf.get_distribution(Id=distribution_id)['Distribution']['DistributionConfig']
        observations['cloudfront_enabled'] = dist['Enabled']
        observations['viewer_protocol_policy'] = dist['DefaultCacheBehavior']['ViewerProtocolPolicy']
        observations['oac_ids'] = [o.get('OriginAccessControlId', '') for o in dist['Origins']['Items']]
    except Exception as e:
        observations['distribution_error'] = str(e)
    record('tool_result', tool='aws_readonly_audit', bucket=bucket, distribution_id=distribution_id, result=observations)
    return observations


def approved_aws_cli(args: list[str], approval: bool = False) -> dict:
    """Strict list of safe, bounded commands. All mutations require explicit confirmation."""
    allowed_prefixes = [('aws', 's3', 'sync'), ('aws', 'cloudfront', 'create-invalidation')]
    if not approval:
        raise PermissionError('Human approval required before AWS modification')
    if not any(tuple(args[:len(prefix)]) == prefix for prefix in allowed_prefixes):
        raise ValueError('Command not in strict tool allowlist')
    if any(x.startswith('--') and x in ('--delete', '--profile', '--endpoint-url') for x in args):
        raise ValueError('Unsupported risky flag')
    record('tool_request', tool='approved_aws_cli', argv=args, human_approved=True)
    completed = subprocess.run(args, capture_output=True, text=True, timeout=180)
    result = {'returncode': completed.returncode, 'stdout': completed.stdout[-2500:], 'stderr': completed.stderr[-2500:]}
    record('tool_result', tool='approved_aws_cli', result=result)
    return result

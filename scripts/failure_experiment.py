"""Reversible recovery demo using a disposable CloudFront/S3 probe object."""
import argparse
import json
import os
import re
import uuid
from urllib.parse import urlparse

import requests
from dotenv import load_dotenv

from agents.core import ROOT, record

EXPECTED_BUCKET = 'csce412hiya-website-2026'
EXPECTED_DOMAIN = 'csce412hiya.link'
KEY_PREFIX = 'project5-recovery-probe-'
STATE_PATH = ROOT / 'outputs' / 'failure_experiment_state.json'
PUBLIC_ACCESS_SETTINGS = (
    'BlockPublicAcls',
    'IgnorePublicAcls',
    'BlockPublicPolicy',
    'RestrictPublicBuckets',
)


def _site_url() -> str:
    site_url = os.environ.get('SITE_URL', '')
    parsed = urlparse(site_url)
    if (parsed.scheme != 'https' or parsed.hostname != EXPECTED_DOMAIN
            or parsed.username or parsed.password or parsed.path not in ('', '/')
            or parsed.query or parsed.fragment):
        raise ValueError(f'SITE_URL must be https://{EXPECTED_DOMAIN}')
    return site_url.rstrip('/')


def _target():
    bucket = os.environ.get('S3_BUCKET', '')
    if bucket != EXPECTED_BUCKET:
        raise ValueError(f'S3_BUCKET must be set to the confirmed project bucket {EXPECTED_BUCKET}')
    _site_url()

    import boto3

    s3 = boto3.client('s3')
    cloudfront = boto3.client('cloudfront')
    access_block = s3.get_public_access_block(Bucket=bucket)['PublicAccessBlockConfiguration']
    if any(access_block.get(setting) is not True for setting in PUBLIC_ACCESS_SETTINGS):
        raise RuntimeError('Refusing experiment: all four S3 public-access-block settings must be true')

    distributions = cloudfront.list_distributions().get('DistributionList', {}).get('Items', [])
    matches = [
        item for item in distributions
        if EXPECTED_DOMAIN in item.get('Aliases', {}).get('Items', [])
    ]
    if len(matches) != 1:
        raise RuntimeError('Refusing experiment: expected exactly one matching CloudFront alias')

    distribution = matches[0]
    if distribution.get('Status') != 'Deployed' or not distribution.get('Enabled'):
        raise RuntimeError('Refusing experiment: matching CloudFront distribution must be enabled and Deployed')
    origins = distribution.get('Origins', {}).get('Items', [])
    bucket_origins = [
        origin for origin in origins
        if re.match(rf'^{re.escape(bucket)}\.s3(?:[.-]|$)', origin.get('DomainName', ''))
    ]
    if len(bucket_origins) != 1 or not bucket_origins[0].get('OriginAccessControlId'):
        raise RuntimeError('Refusing experiment: expected one matching S3 origin protected by OAC')
    return s3, cloudfront, distribution['Id']


def _state() -> dict:
    if not STATE_PATH.is_file():
        raise FileNotFoundError('No recovery probe state exists; run the approved seed action first')
    state = json.loads(STATE_PATH.read_text(encoding='utf-8'))
    probe_id = state.get('probe_id', '')
    if not re.fullmatch(r'[0-9a-f]{32}', probe_id):
        raise ValueError('Recovery probe state has an invalid probe ID')
    expected_key = f'{KEY_PREFIX}{probe_id}.txt'
    expected_content = f'CSCE 412 recovery probe {probe_id}\n'
    if (state.get('key') != expected_key
            or state.get('bucket') != EXPECTED_BUCKET
            or state.get('content') != expected_content
            or state.get('status') not in ('seeded', 'broken', 'restored', 'cleaned')):
        raise ValueError('Recovery probe state is invalid or does not match the project target')
    return state


def _head_or_none(s3, bucket: str, key: str):
    from botocore.exceptions import ClientError

    try:
        return s3.head_object(Bucket=bucket, Key=key)
    except ClientError as exc:
        code = exc.response.get('Error', {}).get('Code')
        if code in ('404', 'NoSuchKey', 'NotFound'):
            return None
        raise


def _assert_probe_owned(s3, state: dict):
    head = _head_or_none(s3, state['bucket'], state['key'])
    if head is not None and head.get('Metadata', {}).get('project5-recovery-probe') != state['probe_id']:
        raise RuntimeError('Refusing to overwrite or delete an object without the matching recovery-probe marker')
    return head


def _save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = STATE_PATH.with_suffix('.tmp')
    temporary_path.write_text(json.dumps(state, indent=2), encoding='utf-8')
    temporary_path.replace(STATE_PATH)


def _invalidate(cloudfront, distribution_id: str, key: str, action: str) -> None:
    response = cloudfront.create_invalidation(
        DistributionId=distribution_id,
        InvalidationBatch={
            'Paths': {'Quantity': 1, 'Items': [f'/{key}']},
            'CallerReference': f'project5-recovery-{action}-{uuid.uuid4().hex}',
        },
    )
    invalidation_id = response['Invalidation']['Id']
    cloudfront.get_waiter('invalidation_completed').wait(
        DistributionId=distribution_id,
        Id=invalidation_id,
        WaiterConfig={'Delay': 10, 'MaxAttempts': 60},
    )


def check_probe() -> dict:
    """Observe the probe URL for the verification agent without changing AWS."""
    state = _state()
    url = f"{_site_url()}/{state['key']}"
    expected_available = state['status'] in ('seeded', 'restored')
    try:
        response = requests.get(url, timeout=15, allow_redirects=True)
        final_url = urlparse(response.url)
        available = (
            response.ok
            and final_url.scheme == 'https'
            and final_url.hostname == EXPECTED_DOMAIN
            and response.text == state['content']
        )
        result = {
            'url': url,
            'http_status': response.status_code,
            'expected_available': expected_available,
            'available': available,
            'ok': available == expected_available,
        }
    except requests.RequestException as exc:
        result = {
            'url': url,
            'expected_available': expected_available,
            'available': False,
            'ok': False,
            'error': str(exc),
        }
    record('tool_result', tool='check_recovery_probe', result=result)
    return result


def _mutate(action: str) -> None:
    s3, cloudfront, distribution_id = _target()
    if action == 'seed':
        if STATE_PATH.is_file():
            previous = _state()
            if previous['status'] != 'cleaned':
                raise RuntimeError('A probe already exists; restore and clean it before starting another')
        probe_id = uuid.uuid4().hex
        state = {
            'probe_id': probe_id,
            'bucket': EXPECTED_BUCKET,
            'key': f'{KEY_PREFIX}{probe_id}.txt',
            'content': f'CSCE 412 recovery probe {probe_id}\n',
            'status': 'seeded',
        }
        if _head_or_none(s3, state['bucket'], state['key']) is not None:
            raise RuntimeError('Refusing to overwrite the generated probe key because it already exists')
        s3.put_object(
            Bucket=state['bucket'],
            Key=state['key'],
            Body=state['content'].encode('utf-8'),
            ContentType='text/plain; charset=utf-8',
            CacheControl='no-store',
            Metadata={'project5-recovery-probe': probe_id},
        )
        _save_state(state)
    else:
        state = _state()
        if action == 'break':
            if state['status'] not in ('seeded', 'restored'):
                raise RuntimeError('The probe must be seeded or restored before it can be removed')
            head = _assert_probe_owned(s3, state)
            if head is None:
                raise RuntimeError('The recovery probe is already missing; cannot record a new break action')
            s3.delete_object(Bucket=state['bucket'], Key=state['key'])
            state['status'] = 'broken'
            _save_state(state)
        elif action == 'restore':
            if state['status'] != 'broken':
                raise RuntimeError('The probe must be in the broken state before it can be restored')
            _assert_probe_owned(s3, state)
            s3.put_object(
                Bucket=state['bucket'],
                Key=state['key'],
                Body=state['content'].encode('utf-8'),
                ContentType='text/plain; charset=utf-8',
                CacheControl='no-store',
                Metadata={'project5-recovery-probe': state['probe_id']},
            )
            state['status'] = 'restored'
            _save_state(state)
        elif action == 'cleanup':
            if state['status'] != 'restored':
                raise RuntimeError('Restore and verify the probe before cleaning it up')
            head = _assert_probe_owned(s3, state)
            if head is None:
                raise RuntimeError('The recovery probe is already missing; cannot clean it up')
            s3.delete_object(Bucket=state['bucket'], Key=state['key'])
            state['status'] = 'cleaned'
            _save_state(state)
        else:
            raise ValueError(f'Unsupported mutation action: {action}')

    _invalidate(cloudfront, distribution_id, state['key'], action)
    record(
        'failure_experiment_action',
        action=action,
        key=state['key'],
        human_approved=True,
        invalidation_completed=True,
        note='Only the disposable recovery-probe object was changed; the five website pages were not modified.',
    )
    print(f'{action.capitalize()} complete for disposable probe {state["key"]}; CloudFront invalidation completed.')


def main() -> None:
    load_dotenv(ROOT / '.env')
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=['seed', 'break', 'restore', 'verify', 'cleanup'])
    parser.add_argument('--approve', action='store_true', help='Explicitly approve changing the disposable probe object')
    args = parser.parse_args()

    if args.action == 'verify':
        print(json.dumps(check_probe(), indent=2))
        return
    if not args.approve:
        raise PermissionError('Human approval required before changing AWS; rerun with --approve')
    record(
        'failure_experiment_request',
        action=args.action,
        bucket=EXPECTED_BUCKET,
        human_approved=True,
    )
    try:
        _mutate(args.action)
    except Exception as exc:
        record(
            'failure_experiment_error',
            action=args.action,
            error=str(exc),
            human_approved=True,
        )
        raise


if __name__ == '__main__':
    main()

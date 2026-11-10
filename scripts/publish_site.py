"""Approval-gated real S3 upload and CloudFront cache invalidation."""
import argparse
from pathlib import Path
from dotenv import load_dotenv
from agents.core import ROOT, record
from agents.tools import approved_aws_cli
import os

def main():
    load_dotenv(ROOT/'.env')
    parser=argparse.ArgumentParser()
    parser.add_argument('--approve', action='store_true', help='Explicit human authorization for publishing')
    args=parser.parse_args()
    bucket=os.getenv('S3_BUCKET', '<set S3_BUCKET in .env>'); distribution=os.getenv('CLOUDFRONT_DISTRIBUTION_ID', '<set CLOUDFRONT_DISTRIBUTION_ID in .env>')
    if not args.approve:
        print('Dry run only. To publish, review target and rerun with --approve')
        print(f'Would sync {ROOT / "website"} to s3://{bucket}/ and invalidate {distribution}')
        return
    if bucket.startswith('<') or distribution.startswith('<'):
        raise ValueError('Set S3_BUCKET and CLOUDFRONT_DISTRIBUTION_ID in .env before approving')
    a=approved_aws_cli(['aws','s3','sync',str(ROOT/'website'),f's3://{bucket}/'],approval=True)
    if a['returncode'] != 0: raise RuntimeError('S3 sync failed; see execution logs')
    b=approved_aws_cli(['aws','cloudfront','create-invalidation','--distribution-id',distribution,'--paths','/*'],approval=True)
    if b['returncode'] != 0: raise RuntimeError('CloudFront invalidation failed')
    record('site_publish_requested',bucket=bucket,distribution_id=distribution, human_approved=True)

if __name__=='__main__':main()

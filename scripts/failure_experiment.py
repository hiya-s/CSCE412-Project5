"""Controlled, reversible S3 removal of a single page. Run ONLY against your own bucket."""
import argparse
import os
from pathlib import Path
from dotenv import load_dotenv
from agents.core import ROOT, record
from agents.tools import check_http_site

def main():
    load_dotenv(ROOT/'.env')
    p=argparse.ArgumentParser()
    p.add_argument('action',choices=['break','restore','verify'])
    p.add_argument('--approve',action='store_true',help='I approve changing this test object in my bucket')
    a=p.parse_args()
    bucket=os.environ.get('S3_BUCKET'); distribution=os.environ.get('CLOUDFRONT_DISTRIBUTION_ID')
    if a.action=='verify':
        print(check_http_site(os.environ['SITE_URL']));return
    if not a.approve: raise PermissionError('Human approval required: rerun with --approve')
    if not bucket or not distribution: raise ValueError('Set S3_BUCKET and CLOUDFRONT_DISTRIBUTION_ID')
    import boto3
    s3=boto3.client('s3');cf=boto3.client('cloudfront')
    key='about.html'
    if a.action=='break':
        # A local website copy must exist before deliberately removing the cloud object.
        assert (ROOT/'website'/key).exists(), 'Local recovery file missing'
        s3.delete_object(Bucket=bucket,Key=key)
    else:
        s3.upload_file(str(ROOT/'website'/key),bucket,key,ExtraArgs={'ContentType':'text/html'})
    inv=cf.create_invalidation(DistributionId=distribution,InvalidationBatch={
        'Paths':{'Quantity':1,'Items':['/about.html']},'CallerReference':f'project5-{a.action}-{__import__("time").time_ns()}'})
    record('failure_experiment_action',action=a.action,bucket=bucket,key=key, human_approved=True,
           cloudfront_invalidation_id=inv['Invalidation']['Id'],note='Wait for CloudFront invalidation to complete, then run verify')

if __name__=='__main__':main()

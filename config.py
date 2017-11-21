import os

os.environ["S3_BUCKET_NAME"] = "ejjagiripics"
os.environ["S3_ACCESS_KEY"] = "AKIAJRTWS7KFCAMNHZNQ"
os.environ["S3_SECRET_ACCESS_KEY"] = "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"

S3_BUCKET	= os.environ.get("S3_BUCKET_NAME")
S3_KEY 		= os.environ.get("S3_ACCESS_KEY")
S3_SECRET	= os.environ.get("S3_SECRET_ACCESS_KEY")
S3_LOCATION	= 'http://{}.s3.amazonaws.com/'.format(S3_BUCKET)

SECRET_KEY 	= os.urandom(32)
DEBUG		= True
PORT		= 5000


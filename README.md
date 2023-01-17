# extract-np-list

Extract a PDF file from email and save it to S3 bucket

# Create and Upload Package

## Create Package Dir

pip install --target ./package pdfminer.six pytz

## Create Zip

cd package
zip -r ../my-deployment-package.zip .

## Add the Lambda Function

cd ..
zip my-deployment-package.zip lambda_function.py

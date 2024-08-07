#!/bin/bash 
set -ex
export ENV=$1

if [ ${ENV,,} == 'dev' ]; then
    export COMPUTE_PROJECT="us-gcp-ame-con-c2dbd-npd-1"
    #export SERVICE_ACCOUNT="usa-vivprasad-dlp@us-gcp-ame-con-c2dbd-npd-1.iam.gserviceaccount.com"
    export TEMPLATE_LOCATION="gs://my-dlp-bucket01/dev/dataflow/template/data_ingestion_dataflow.json"
else
    echo "Environment not mentioned."
fi

gcloud config set project ${COMPUTE_PROJECT}

# create template
echo "Data flow job running in ${ENV}"
python data_ingestion_dataflow.py --env ${ENV}

# # # create job    234567890-dasZ
gcloud dataflow jobs run data_ingestion_dataflow.py \
 --gcs-location=$TEMPLATE_LOCATION \
 --disable-public-ips \
 --region='us-east4'
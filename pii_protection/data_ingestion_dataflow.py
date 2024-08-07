import google.auth
import argparse
import yaml
import logging
import json
import hashlib
import os
import sys
import ast
import time,datetime
import google.cloud.dlp
import base64
import apache_beam as beam
from typing import List
from googleapiclient import discovery
from google.cloud import storage
from datetime import datetime
from apache_beam import pvalue
from google.auth.transport import requests
from oauth2client.client import GoogleCredentials
from apache_beam import DoFn, GroupByKey, io, ParDo, Pipeline, window, WithKeys, WindowInto
from apache_beam.options.pipeline_options import PipelineOptions
from apache_beam.io import WriteToText
from apache_beam.transforms import trigger
from apache_beam.transforms.window import FixedWindows, GlobalWindows
from apache_beam.io.fileio import FileSink

class GetMessage(beam.DoFn):

    def __init__(self):
        self.record_count = 1
        
    def process(self,element):
        grp_key,pubsub_data = element
        for record in pubsub_data:
            yield record

class AddTimestamp(beam.DoFn):
    ''' Add Timestamp for grouping '''
    def process(self,element,publish_time=beam.DoFn.TimestampParam):
        publish_time = datetime.utcfromtimestamp(float(publish_time)).strftime("%Y-%m-%d %H:%M:%S")
        output = (publish_time,element)
        yield output

class GroupWindowsIntoBatches(beam.PTransform):
    
    def expand(self,pcoll):
        return (
            pcoll
            | "Windows into Fixed Intervals" >> beam.WindowInto(window.FixedWindows(int(window_fixed_second)),
                                                                allowed_lateness = 10,
                                                                trigger = trigger.Repeatedly(
                                                                    trigger.AfterAny(
                                                                        trigger.AfterCount(int(windowing_count)),
                                                                        trigger.AfterProcessingTime(int(windowing_processing_sec))
                                                                    )
                                                                ),
                                                                accumulation_mode=trigger.AccumulationMode.DISCARDING)
            | "Add Publish Timestamp as Key" >> beam.ParDo(AddTimestamp())
            | "Group by Key" >> GroupByKey()
        )

class mask_pii_data(beam.DoFn):
    def __init__(self,config):
        self.project = config['project']
        self.config = config
    
    def process(self,element):
        try:
            logging.info(f'element {element}')

            def deidentify_replace_fpe(project,input_str,deidentify_template):
                # Instantiate a client
                dlp = google.cloud.dlp_v2.DlpServiceClient()

                # Convert the project id into a full resource id.
                parent = f"projects/{project}"

                deid_template = self.config['deidentify_template']
                inspect_template = self.config['inspect_template']

                get_inspect_config = dlp.get_inspect_template(request={"name": inspect_template})
                get_deid_config = dlp.get_deidentify_template(request={"name": deid_template})

                inspect_config = get_inspect_config.inspect_config
                deidentify_config = get_deid_config.deidentify_config

                # Convert string to item
                item = {"value": input_str}

                # Call the API
                mask_response = dlp.deidentify_content(
                    request={
                        "parent": parent,
                        "deidentify_config": deidentify_config,
                        "inspect_config": inspect_config,
                        "item": item,
                    }
                )
                # Print results
                return mask_response.item.value

            deidentify_template = self.config['deidentify_template']
            masked_msg = deidentify_replace_fpe(self.project,element,deidentify_template)
            msg = ast.literal_eval(masked_msg)
            logging.info(f'masked_msg {msg}')
            yield msg
        except:
            print("Error while masking data")

def run(args_env):
    env = args_env
    global window_fixed_second,windowing_count,windowing_processing_sec

    with open('data_ingestion_config.yaml','r') as yamlfile:
        config = yaml.load(yamlfile, Loader=yaml.BaseLoader)
    cfg = config[env]

    window_fixed_second = cfg['window_fixed_second']
    windowing_count = cfg['windowing_count']
    windowing_processing_sec = cfg['windowing_processing_sec']
    pub_sub_subscription = cfg['pub_sub_subscription']
        
    jobname = cfg['jobname']
    project = cfg['project']
    bq_dataset = cfg['bq_dataset']
    bq_table_name = cfg['bq_table_name']
    table_schema = cfg['schema']
    table_spec = f'{project}:{bq_dataset}.{bq_table_name}'
    logging.info(f'Job Starting {jobname}')
    static_input = '{"user_id": 2632314, "user_name": "Caroline Gibbs", "user_email": "cdavidson@example.net", "user_address": "123 Main Street", "user_city": "Port Charlesville", "user_country": "Uganda", "user_phone": "001-193-157-5539x40496", "transaction_id": 12345, "transaction_date": "1994-02-18 08:02:20", "user-ssn": "518-22-0504", "product_id": 69009, "product_name": "brown", "product_price": "992.59", "quantity": 2, "payment_type": "credit_card", "provider": "VISA 16 digit", "card_number": "348280981352296", "expiration_date": "10/26", "cardholder_name": "Allison Hull", "billing_address": "833 Heather Loaf\\nDaniellemouth, NM 15522"}'    
    
    pipeline_args = [   '--project', cfg['project'],
                        '--jobname', cfg['jobname'],
                        '--setup_file', cfg['setup_file'],
                        '--save_main_session', 'True',
                        #'--runner',cfg['runner'],
                        '--runner','DirectRunner',
                        '--staging_location', cfg['staging_location'],
                        '--temp_location', cfg['temp_location'],
                        '--region', cfg['region'],
                        '--worker_zone', cfg['worker_zone'],
                        '--worker_machine_type',cfg['worker_machine_type'],
                        '--template_location', cfg['template_location'],
                        '--worker_disk_type', cfg['worker_disk_type'],
                        '--disk_size_gb', cfg['disk_size_gb'],
                        '--max_num_workers',cfg['max_num_workers'],
                        '--no_use_public_ips',
                        '--subnetwork',cfg['subnetwork'],
                        '--autoscaling_algorithm', cfg['autoscaling_algorithm'],
                        '--labels',cfg['label']
                    ]
    credentials,_ = google.auth.default(scopes=['googleapis.com/auth/cloud-platform'])
    
    try:
        pipeline_options = PipelineOptions(
            pipeline_args, streaming=True, save_main_session=True
            )
        with Pipeline(options=pipeline_options) as pipeline:
            streaming_process = (
                pipeline
                #| "Read from static input" >> beam.Create([static_input]))
                | "Read from Pub/Sub" >> beam.io.ReadFromPubSub(subscription=pub_sub_subscription)
                | "UTF-8 bytes to String" >> beam.Map(lambda msg:msg.decode('utf-8'))
                | "Windowing" >> GroupWindowsIntoBatches()
                | "Get Message" >> beam.ParDo(GetMessage())
                | "Reschuffle Records" >> beam.Reshuffle())
            masked_data = streaming_process | "Mask PII Data with DLP" >> beam.ParDo(mask_pii_data(cfg))
            write_to_bq = masked_data | "Write to BQ" >> beam.io.WriteToBigQuery(
                                                        table_spec,
                                                        schema=table_schema,
                                                        write_disposition=beam.io.BigQueryDisposition.WRITE_APPEND,
                                                        create_disposition=beam.io.BigQueryDisposition.CREATE_IF_NEEDED)
    
    except Exception as e:
        logging.info(f'error {e}')
        
if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('--env', required=True,
                        help='Add Environment - Dev/Prod'
                        )
    args = parser.parse_args()
    logging.getLogger().setLevel(logging.INFO)
    run(args.env)
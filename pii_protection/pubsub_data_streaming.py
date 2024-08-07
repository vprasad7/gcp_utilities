import json
import random
import time
from faker import Faker
from google.cloud import pubsub_v1

fake = Faker()
starttime = time.monotonic()

def create_fake_data(publisher):
    data_str = ""

    #for i in range(no_of_records):
    data_str = (
                    {
                        "user_id": fake.pyint(min_value = 0, max_value = 9999999, step = 1),
                        "user_name": fake.name(),
                        "user_email": fake.email(),
                        "user_address": "123 Main Street",
                        "user_city": fake.city(),
                        "user_country": fake.country(),
                        "user_phone": fake.phone_number(),
                        "transaction_id": 12345,
                        "transaction_date": fake.date(pattern = '%Y-%m-%d %H:%m:%S'),
                        "user-ssn": fake.ssn(),
                        "product_id": fake.pyint(min_value = 10000, max_value = 99999, step = 1),
                        "product_name": fake.domain_word(),
                        "product_price": f"{fake.pydecimal(left_digits=3, right_digits=2, positive=False, min_value=None, max_value=None)}",
                        "quantity": 2,
                        "payment_type": "credit_card",
                        "provider" : fake.credit_card_provider(),
                        "card_number": fake.unique.credit_card_number(card_type='visa16'),
                        "expiration_date": f"{fake.month()}/26",
                        "cardholder_name": fake.name(),
                        "billing_address": fake.address()
                    }
                )
    data = json.dumps(data_str).encode("utf-8")
    # When you publish a message, the client returns a future.
    future = publisher.publish(topic_path, data)
    print(f'message published {data}')



publisher = pubsub_v1.PublisherClient()
project_id = "us-gcp-ame-con-c2dbd-npd-1"
topic_id = "myPubSub01"
topic_path = publisher.topic_path(project_id, topic_id)
while True:
    create_fake_data(publisher)
    print("Waiting for 10 seconds...")
    time.sleep(10)
    
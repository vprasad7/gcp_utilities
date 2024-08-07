from typing import List
import google.cloud.dlp
import base64

project = 'us-gcp-ame-con-c2dbd-npd-1'
input_str = 'My name is Alicia Abernathy, and my email address is aabernathy@example.com and SSN number 123456789'
deidentify_template = 'myTemplate01'

def deidentify_replace_fpe(
    project: str,
    input_str: str,
    deidentify_template
):
    # Instantiate a client
    dlp = google.cloud.dlp_v2.DlpServiceClient()

    # Convert the project id into a full resource id.
    parent = f"projects/{project}"

    # Construct deidentify configuration dictionary
    deidentify_config = get_deidentify_config(project,deidentify_template)
    print(type(deidentify_config))

    # Convert string to item
    item = {"value": input_str}

    # Call the API
    response = dlp.deidentify_content(
        request={
            "parent": parent,
            "deidentify_config": deidentify_config,
            "item": item,
        }
    )

    # Print results
    print(response.item.value)

def get_deidentify_config(project: str,deidentify_template):

    # Instantiate a client.
    dlp = google.cloud.dlp_v2.DlpServiceClient()

    # Convert the project id into a full resource id.
    parent = f"projects/{project}"

    # Call the API.
    response = dlp.list_deidentify_templates(request={"parent": parent})

    for template in response:
        if template.display_name == deidentify_template:
            deidentify_config = template.deidentify_config
            break
    print(deidentify_config)
    return deidentify_config

deidentify_replace_fpe(project,input_str,deidentify_template)

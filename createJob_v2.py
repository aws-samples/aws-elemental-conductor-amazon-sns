# Sample code for Elemental API call for creating a job authored by P Liang
# Contact Liang pengchl@amazon.com if you have any question

import xml.etree.ElementTree as ET
import subprocess
import logging
import datetime
import configparser
import sys
import re
import chardet

logging.basicConfig(filename='createJob.log',level=logging.DEBUG)

# This script is aimed to have a Elemental Conductor job started, with predefined profile and modified parameters.
# 1. Get specfic profile xml by parsing template.xml
# 2. Get input file uri and start, end time code from args
# 3. modify new Xml: you modify <file_input>, <input_clipping>, <timecode_config>.
# 4. Using AUTH_CURL_CMD to POST to create a job
# 5. Log job Id for future status checking

# Load configurations from config.ini
config = configparser.ConfigParser()
config.read('config.ini')
#PROFILE_ID = config['DEFAULT']['PROFILE_ID']
#AUTH_CURL_GET = config['DEFAULT']['AUTH_CURL_GET']
AUTH_CURL_POST = config['DEFAULT']['AUTH_CURL_POST']
TEMPLATE = config['DEFAULT']['TEMPLATE']

# Task 1
template = ET.ElementTree(file=TEMPLATE)
#print(profile_xml)

# Task 2
input_uri = sys.argv[1]
start_timecode = sys.argv[2]
end_timecode = sys.argv[3]
#print(input_uri)

# Task 3
template.find('input/file_input/uri').text = input_uri
template.find('input/input_clipping/start_timecode').text = start_timecode
template.find('input/input_clipping/end_timecode').text = end_timecode

#pretty_xml = minidom.parseString(ET.tostring(template)).toprettyxml(indent="     ")
thisJobTemplate = "./tmp/" + input_uri.split("/")[-1] + "-" + start_timecode + "-" + end_timecode +".xml"
template.write(thisJobTemplate)

output = subprocess.check_output(AUTH_CURL_POST.replace("jobtemplate.xml",thisJobTemplate), shell = True)
encode_type = chardet.detect(output)
output = output.decode(encode_type['encoding'])

jobId = re.findall(r"/jobs/\d+", output)[0].replace("/jobs/","")

print(jobId)
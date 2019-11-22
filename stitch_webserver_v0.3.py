#!/usr/bin/env python
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from natsort import natsorted
import xml.etree.ElementTree as ET
import socketserver
import sqlite3
import logging
import datetime
import math
import subprocess
import uuid
import re
import os
import configparser

# Load configurations from config.ini
config = configparser.ConfigParser()
config.read('config.ini')
WATCH_PATH = config['DEFAULT']['WATCH_PATH']  # Addon Watch Folder
OUTPUT_FOLDER = config['DEFAULT']['OUTPUT_FOLDER']
CLIPSIZE = config['DEFAULT']['CLIPSIZE']  
AUTH_CURL_CMD = config['DEFAULT']['AUTH_CURL_CMD']
DB_PATH = config['DEFAULT']['DB_PATH']
ADDON_PATH = config['DEFAULT']['ADDON_PATH']
WEBSERVER_ADDR = config['DEFAULT']['WEBSERVER_ADDR']
SERVER_PORT = config['DEFAULT']['SERVER_PORT']
NO_OF_OUTPUTS = config['DEFAULT']['NO_OF_OUTPUTS']
OUTPUT1_PREFIX = config['DEFAULT']['OUTPUT1_PREFIX']
OUTPUT2_PREFIX = config['DEFAULT']['OUTPUT2_PREFIX']
OUTPUT3_PREFIX = config['DEFAULT']['OUTPUT3_PREFIX']
OUTPUT4_PREFIX = config['DEFAULT']['OUTPUT4_PREFIX']
OUTPUT5_PREFIX = config['DEFAULT']['OUTPUT5_PREFIX']

logging.basicConfig(filename='stitchserver.log',level=logging.DEBUG)

class MyHandler(BaseHTTPRequestHandler):
    
    def _send_response_200(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()
    '''
    def _send_response_302(self):
        self.send_response(302)
        location = URL_ROUTE.get(self.path, DEFAULT_URL)        
        self.send_header('Location', location)
        self.end_headers()
        self.log_message('Redirect to "%s"'%location)

    def do_HEAD(self):
        if self.path == '/':
            self._send_response_200()
        else:
            self._send_response_302()

    def do_GET(self):
        #Respond to a GET request.
        self.do_HEAD()
        self.wfile.write('<HTML>GET OK.<BR>')
        pass
    '''
    def do_POST(self):
        try:
            #self.do_HEAD()
            self._send_response_200
            #content = self.rfile.read(int(self.headers.getheader('content-length')))
            #self.wfile.write('<HTML>POST OK.<BR>')
            content_length = int(self.headers['Content-Length']) # <--- Gets the size of data
            content = self.rfile.read(content_length) # <--- Gets the data itself
            #self.log_message('POST data: %s'%content)
            
            # if status of the job is complete then do:
            # 1. get job file name from job detail
            # 2. locate corresponding record in sqlite table VideoSegDetails
            # 3. update sqlite record (Task S1.3)
            # 4. check whether all the sub transcoding jobs complete
            # 5. join to one video file
            # N/A 6. stitch audio and video together

            # 1. get job file name from job detail; 
            # 1.1 get jobId
            # 1.2 get file path
            # print(content)
            # <job href="/jobs/34"><status>complete</status></job>
            xml_root = ET.fromstring(content)
            logging.info('************-------job status and jobId--------*************')
            jobId = xml_root.attrib['href']
            status = xml_root.find('status').text
            logging.info('[%s]Status: %s', datetime.datetime.now(), status)
            logging.info('[%s]JobId: %s', datetime.datetime.now(), jobId)

            if status == 'complete':
                #1. call Elemental api to get file name
                '''
                <?xml version="1.0" encoding="UTF-8"?>
                <job href="/jobs/4" product="Elemental Server + Audio Normalization Package + Audio Decode Package + Audio Package + HEVC Package + Motion Image Inserter Package + AVC-I
                + HEVC 4:2:2 Package" version="2.13.0.403124">
                <input>
                    <active>false</active>
                    <filter_enable>Disable</filter_enable>
                    <id>4</id>
                    <no_psi>false</no_psi>
                    <order>1</order>
                    <status>pending</status>
                    <timecode_source>embedded</timecode_source>
                    <file_input>
                    <certificate_file nil="true"/>
                    <id>4</id>
                    <uri>/data/server/incoming/cctv/juzijie-1-of-7_hevc.mp4</uri>
                '''
                logging.info("************-------Start calling Elemental Server--------*************")
                output = subprocess.check_output(AUTH_CURL_CMD + jobId, shell=True)
                #print(output)
                xml_root = ET.fromstring(output)
                #inputFileName = /data/server/incoming/cctv/juzijie-1-of-7_hevc.mp4
                inputFileName = xml_root.find('input/file_input/uri').text
                #prefix = inputFileName.split('.')[0]
                #suffix = inputFileName.split('.')[-1]

                # * For multiple output groups, iterate and save all full_uris to outjobfullURIs
                outjobfullURIs = ''
                name_modifiers = ''
                for f in xml_root.iter('full_uri'):
                    outjobfullURI = f.text #/data/server/outgoing/cctv/single/juzijie-1-of-7_hevc.mp4
                    outjobfullURIs = outjobfullURIs + ' ' + outjobfullURI
                    logging.info("************-------Output Job Full URI--------*************")
                    logging.info('[%s]%s', datetime.datetime.now(), outjobfullURI)
                for n in xml_root.iter('name_modifier'):
                    name_modifier = n.text #_h264
                    name_modifiers = name_modifiers + ' '  + name_modifier
                    logging.info("************-------Output file name_modifier--------*************")
                    logging.info('[%s]%s', datetime.datetime.now(), name_modifier)

                #2,#3. locate and update corresponding record in sqlite table VideoSegDetails
                conn = sqlite3.connect(DB_PATH)
                cursorObject = conn.cursor()
                #(joinstatus, jointime, transcoded_time, transcoded_jobIds)
                # inputFileName = /data/server/incoming/cctv/juzijie-1-of-7_hevc.mp4 ==> juzijie.mp4'
                # inputFileName = /data/server/incoming/cctv/movie2.5M-SD-4m58s-7-of-7-sd.mp4 ==> movie2.5M-SD-4m58s.mp4'
                reg = "-\d+-of-\d+\.\w+"
                p = re.compile(r''+reg+'')
                #sourceFilePath = WATCH_PATH + re.sub(p,"",inputFileName.split('/')[-1])
                sourceFilePath = inputFileName
                logging.info("************-------sourceFilePath--------*************")    
                logging.info('[%s]%s', datetime.datetime.now(), sourceFilePath)
                # sourceFilePath = /data/server/uhd/juzijie.mp4
                #cursor = cursorObject.execute("SELECT transcoded_jobIds from VideoSegDetails where full_file_path = ?", (sourceFilePath))
                #jobIds = ''
                #for row in cursor:
                #    jobIds = row[0]

                
                logging.info("************-------Updating Output Job URIs & name_modifiers--------*************")

                # * For multiple outputs, update all the output full_uris to the same record
                # update name_modifiers
                
                #print("UPDATE VideoSegDetails set transcoded_time = s%, transcoded_jobIds = transcoded_jobIds || s%, outjoburis = outjoburis || s% \
                #                      where full_file_path = s% ", str(datetime.datetime.now()), ' ' + jobId.split('/')[-1], ' ' + outjobfullURI, sourceFilePath)
                cursorObject.execute("UPDATE VideoSegDetails set transcoded_time = ?, transcoded_jobIds = transcoded_jobIds || ?, outjoburis = outjoburis || ?, name_modifiers = ? \
                                      where full_file_path = ? ", (datetime.datetime.now(), ' ' + jobId.split('/')[-1], ' ' + outjobfullURIs, name_modifiers, sourceFilePath))
                #cursorObject.execute("UPDATE VideoSegDetails set transcoded_time = ? ", datetime.datetime.now())

                conn.commit()

                #4. check whether all the sub transcoding jobs complete
                # * For Multiple output groups, get size of name_modifiers then calculate the total segs with this factor
                logging.info("************-------Checking whether all the sub transcoding jobs complete--------*************")
                cursor = cursorObject.execute("SELECT duration, transcoded_jobIds, name_modifiers, max(ID) from VideoSegDetails where full_file_path = ?", (sourceFilePath,))

                logging.info("************-------Checking finished--------*************")
                duration = 0
                transcoded_jobIds = ''
                modifier_size =1 
                for row in cursor:
                    duration = row[0]  
                    transcoded_jobIds = row[1] 
                    modifier_size = len(row[2].strip().split(' '))
                
                totalsegs = int(math.ceil(duration / float(CLIPSIZE))) * modifier_size
                logging.info("************-------totalsegs--------*************")
                logging.info('[%s]%s', datetime.datetime.now(), totalsegs)
                logging.info("************-------transcoded_jobIds--------*************")
                logging.info('[%s]%s', datetime.datetime.now(), transcoded_jobIds.strip().split(' '))

                logging.info("************-------Retrieve record with sourceFilePath--------*************")
                logging.info('[%s]%s', datetime.datetime.now(), sourceFilePath)
                #if all jobs complete
                if totalsegs == len(transcoded_jobIds.strip().split(' ')) * modifier_size:
                    logging.info("************-------All sub transcoding jobs completed--------*************")
                    logging.info("************-------Start joining segmentated files--------*************")
                    '''
                        ffmpeg -f concat -i mylist.txt -c copy output.mp4
                        file '1.mp4'
                        file '2.mp4'
                        file '3.mp4'
                        file '4.mp4'
                        file '5.mp4'
                    '''
                    #Get output job full URIs
                    # * For Multiple outgroups, use name_modifier to stich corresponding files
                    # use name_modifier as regex to filter different file list
                    cursor = cursorObject.execute("SELECT outjoburis, max(ID) from VideoSegDetails where full_file_path = ?", (sourceFilePath,))
                    outuris = ''
                    for row in cursor:
                        outuris = row[0]  
                    logging.info("************-------Segmentated Output Job URIs--------*************")   
                    good_outuris = list(filter(lambda x: x!='', outuris.strip().split(' ')))
                    logging.info('[%s]%s', datetime.datetime.now(), good_outuris) 

                    # For different name_modifier, create different outuri list
                    # Example: name_modifiers = "_hevc-5-of-6 _avc-5-of-6"
                    # Example: good_outuris = [/data/server/cctv/1Out/4K2-5-of-6_avc.ts,/data/server/cctv/1Out/4K2-5-of-6_hevc.ts]
                    outputPrefixes = list(filter(lambda x: x!='_',[OUTPUT1_PREFIX,OUTPUT2_PREFIX,OUTPUT3_PREFIX,OUTPUT4_PREFIX,OUTPUT5_PREFIX]))
                    logging.info('[%s]outputPrefixes:%s', datetime.datetime.now(), outputPrefixes) 
                    for nm in outputPrefixes:
                        #Example: list(filter(lambda x: "_hevc." in x, ["/data/server/cctv/1Out/4K2-5-of-6_avc.ts","/data/server/cctv/1Out/4K2-5-of-6_hevc.ts"]))
                        nm_sorted_outjoburiList = list(filter(lambda x: nm+'.' in x, good_outuris)) #Example value: ['/data/server/cctv/1Out/4K2-5-of-6_hevc.ts']
                        #Create a random list file for concat, delete it after finishing
                        tmpfilename = ADDON_PATH + str(uuid.uuid4()) + '.txt'
                        transcoded_suffix = nm_sorted_outjoburiList[0].split('.')[-1]
                        logging.info("************-------Joining %s Files--------*************", transcoded_suffix)
                        logging.info('[%s]%s', datetime.datetime.now(), nm_sorted_outjoburiList)

                        try: 
                            filelist = open(tmpfilename,'w+')
                        
                            outjoburiList = natsorted(nm_sorted_outjoburiList)
                            logging.info("[%s]outjoburiList: %s.", datetime.datetime.now(), str(outjoburiList))
                            for index in range(len(outjoburiList)):
                                filelist.write("file " + outjoburiList[index])
                                filelist.write("\n")
                                #if index != int(totalsegs/2):
                                #    filelist.write("\n")
                                #iparam = iparam + prefix + '-' + str(index) + '-of-' + str(totalsegs) + name_modifier + '.' + suffix
                        finally:
                            if filelist is not None:
                                filelist.close()    
                        # sourceFilePath = /data/server/uhd/juzijie.mp4
                        input_ext = '.'+sourceFilePath.split('/')[-1].split('.')[-1]
                        logging.info("[%s]About to concat files using command line: %s", datetime.datetime.now(), str(datetime.datetime.now()))
                        logging.info("[%s]ffmpeg -f concat -safe 0 -i " + tmpfilename + " -codec copy " + OUTPUT_FOLDER + \
                                                sourceFilePath.split('/')[-1].replace(input_ext,"") + nm + "." + transcoded_suffix, datetime.datetime.now() )
                        outfileprefix = OUTPUT_FOLDER + sourceFilePath.split('/')[-1].replace(input_ext,"") # /data/server/outging/cctv/2out/tiyu
                        nm_outputfile = outfileprefix + nm + "." + transcoded_suffix # /data/server/outging/cctv/2out/tiyu_hevc.mp4
                        subprocess.check_output("ffmpeg42 -f concat -safe 0 -analyzeduration 2147483647 -probesize 2147483647 -i " + tmpfilename + " -codec copy " +  nm_outputfile, shell = True)

                        logging.info("***********************Finished joining files***********************")
                        logging.info(datetime.datetime.now())
                        
                        # Delete temp list file
                        os.remove(tmpfilename)
                    
                    # Update Join status and join time
                    cursorObject.execute("UPDATE VideoSegDetails set joinstatus = 1, jointime = ? where full_file_path = ?",(datetime.datetime.now(),sourceFilePath))
                    conn.commit()
                conn.close()

        except :
            pass

def main(server_address):
    try:
        server = HTTPServer(server_address, MyHandler)
        print('Serving HTTP on %s port %d ...',server_address[0], server_address[1])
        server.serve_forever()
    except KeyboardInterrupt:
        print('^C received, Shutting Down HTTP Server')
        server.socket.close()

if __name__ == '__main__':
    if sys.argv[1:]:
        port = int(sys.argv[1])
    else:
        port = int(SERVER_PORT)
    server_address = (WEBSERVER_ADDR, port)

    main(server_address)
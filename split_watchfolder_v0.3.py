import sys
import os
import pyinotify
import time
import math
import os
import subprocess
import datetime
import re
import sqlite3
import configparser
import logging
import time
import xml.etree.ElementTree as ET
import chardet

# v0.3 uses ffprobe to get segmentation information which is used to pass to createJob_v2.py.
# Then createJob python script sends transcoding jobs to Elemental Conductor Server with Input clipping info.
# Handle Video seg table, which contains information of video segmentation details:
# id, full_file_path, duration, totalsegs, segtime, seg_filename_pattern, joinstatus, jointime, transcoded_time, transcoded_jobIds, outjoburis, name_modifiers
# id: sequence
# full_file_path: original video file path, e.g. /data/server/uhd/juzijie.mp4
# duration: original video duration in seconds, e.g. 180
# totalsegs: indicates how many segmentations maps a full original video, e.g. 7
# segtime: time record of video splitter's processing done time, e.g. 2019-08-02 09:18:18
# seg_filename_pattern: regex pattern for segmentated file name, e.g. juzijie-\d+-of-\d+.\w+
# joinstatus: indicates whether the segmentated and transcode files have been joined, e.g. 0
# jointime: time record of joining finished, e.g. 2019-08-02 09:28:10
# transcoded_time: update time record when each trancoding job completes, e.g. 2019-08-02 09:38:20
# transcoded_jobIds: update/add job Id when each transcoding job completes, e.g. 3 4 5 17
# outjoburis: output job full uri, e.g. /data/server/outgoing/cctv/single/juzijie-001-of-7_hevc.mp4
# name_modifiers: output job modifiers used to stitch different output clips to the corresponding file, e.g. _hevc _h264
# 
# Table VideoSegDetails Read and Write scenario:
# S1.1 When a segmentation job completes, insert a row with column values (id, full_file_path, duration, totalsegs, segtime, seg_filename_pattern, joinstatus)
# S1.2 When a segmentation job completes, also mv all the segmentated files to Elemental Watchfolder
# S1.3 When a segmentated job transcoding completes, Elemental Server calls webserver localhost:8888 which accepts related job status xml; Then
#      localhost server updates its corresponding row in VideoSegDetails table with column values (joinstatus, jointime, transcoded_time, transcoded_jobIds)
#      When all the transcoding jobs complete, execute ffmpeg join command.


# Load configurations from config.ini
config = configparser.ConfigParser()
config.read('config.ini')
WATCH_PATH = config['DEFAULT']['WATCH_PATH'] # Monitored path
#ELEMENTAL_WATCHFOLDER = config['DEFAULT']['ELEMENTAL_WATCHFOLDER']
#OUTPUT_FOLDER = config['DEFAULT']['OUTPUT_FOLDER']
DB_PATH = config['DEFAULT']['DB_PATH']
CLIPSIZE = config['DEFAULT']['CLIPSIZE']
ADDON_PATH = config['DEFAULT']['ADDON_PATH']
NO_OF_OUTPUTS = config['DEFAULT']['NO_OF_OUTPUTS']
OUTPUT1_PREFIX = config['DEFAULT']['OUTPUT1_PREFIX']
OUTPUT2_PREFIX = config['DEFAULT']['OUTPUT2_PREFIX']
OUTPUT3_PREFIX = config['DEFAULT']['OUTPUT3_PREFIX']
OUTPUT4_PREFIX = config['DEFAULT']['OUTPUT4_PREFIX']
OUTPUT5_PREFIX = config['DEFAULT']['OUTPUT5_PREFIX']
TEMPLATE = config['DEFAULT']['TEMPLATE']

logging.basicConfig(filename='splitserver.log',level=logging.DEBUG)

#Database and table init
conn = sqlite3.connect(DB_PATH)
query = "SELECT name from sqlite_master WHERE type='table' AND name='" + "VideoSegDetails" + "';"
cursor = conn.execute(query)
result = cursor.fetchone()
if result == None:  #If not then create one
    conn.execute('''CREATE TABLE VideoSegDetails
                    (ID INT PRIMARY KEY     ,
                    FULL_FILE_PATH  TEXT    NOT NULL,
                    DURATION        INT     NOT NULL,
                    TOTALSEGS       INT,
                    SEGTIME         TEXT,
                    SEG_FILENAME_PATTERN    TEXT,
                    JOINSTATUS      INT,
                    JOINTIME        TEXT,
                    TRANSCODED_TIME  TEXT,
                    TRANSCODED_JOBIDS TEXT,
                    OUTJOBURIS      TEXT,
                    NAME_MODIFIERS  TEXT);''')
    logging.info("[%s]Table created successfully", datetime.datetime.now())
    conn.close()
conn.close()

if not WATCH_PATH:
    logging.warning("[%s]The WATCH_PATH setting MUST be set.", datetime.datetime.now())
    sys.exit()
else:
    if os.path.exists(WATCH_PATH):
        logging.info('[%s]Found watch path: path=%s.', datetime.datetime.now(), WATCH_PATH)
    else:
        logging.warning('[%s]The watch path NOT exists, watching stop now: path=%s.', datetime.datetime.now(), WATCH_PATH)
        sys.exit()



# callback
class OnIOHandler(pyinotify.ProcessEvent):
    # Handler when a file finishes writing
    def process_IN_CLOSE_WRITE(self, event):
        # logging.info("create file: %s " % os.path.join(event.path, event.name))
        file_path = os.path.join(event.path, event.name)
        if re.findall(r"\w+-\d+-of-\d+\.\w+", file_path):
            return None
        if file_path.find(WATCH_PATH) == -1:
            return None
        logging.info('[%s]***************************************File created:%s.', datetime.datetime.now(), file_path )

        logging.info("[%s]***************************************Start video segmentation now...", datetime.datetime.now())
        #sample command: ffmpeg -i 1.mp4 -f segment -segment_time 10 -segment_format_options movflags=+faststart -c copy -an out%03d-of-7.mp4
        output = subprocess.check_output(("ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", file_path)).strip()
        duration = int(float(output))
        originalfilename = file_path.split('/')[-1]
        totalsegs = int(math.ceil(duration / float(CLIPSIZE)))
        ##input_ext = '.'+originalfilename.split('.')[-1]

        # 循环生成起止时间参数对
        # time_pairs = ( (time.strftime('%H:%M:%S:00', time.gmtime(i*int(CLIPSIZE))),time.strftime('%H:%M:%S:00', time.gmtime((i+1)*int(CLIPSIZE)))) for i in range(totalsegs))
        
        for i in range(0, totalsegs):
            # 针对每个时间切片修改template中的name_modifier
            template = ET.ElementTree(file=TEMPLATE)
            template.findall('output_group/output/name_modifier')[0].text = "-" + str(i) + "-of-" + str(totalsegs) + OUTPUT1_PREFIX
            template.write(TEMPLATE) #更新name_modifier到template.xml

            try:
                template.findall('output_group/output/name_modifier')[1].text = "-" + str(i) + "-of-" + str(totalsegs) + OUTPUT2_PREFIX 
                template.write(TEMPLATE)
                template.findall('output_group/output/name_modifier')[2].text = "-" + str(i) + "-of-" + str(totalsegs) + OUTPUT3_PREFIX
                template.write(TEMPLATE)
                template.findall('output_group/output/name_modifier')[3].text = "-" + str(i) + "-of-" + str(totalsegs) + OUTPUT4_PREFIX
                template.write(TEMPLATE)
                template.findall('output_group/output/name_modifier')[4].text = "-" + str(i) + "-of-" + str(totalsegs) + OUTPUT5_PREFIX
                template.write(TEMPLATE) 
            except IndexError:
                pass

            time_pair = (time.strftime('%H:%M:%S:00', time.gmtime(i*int(CLIPSIZE))),time.strftime('%H:%M:%S:00', time.gmtime((i+1)*int(CLIPSIZE))))
            # 发送源片、起止时间参数给createJob
            jobId = subprocess.check_output("python3 createJob_v2.py " + file_path + " " + time_pair[0] + " " + time_pair[1], shell=True)
            encode_type = chardet.detect(jobId)
            jobId = output.decode(encode_type['encoding'])
            logging.info("[%s]********Clipping Video is sent for transcoding, JobId :%s", jobId)

    
        #S1.1 task
        #S1.1 prepare column data: duration, totalsegs,seg_filename_pattern
        
        segtime = datetime.datetime.now()
        seg_filename_pattern = originalfilename.split('.')[0] + '-\d+-of-\d+\.\w+' #+ originalfilename.split('.')[1]

        logging.info("[%s]***************************************Video Duration:%d", datetime.datetime.now(), duration)
        logging.info("[%s]***************************************Start updating sqlite...", datetime.datetime.now())

        #S1.1 insert into table
        conn = sqlite3.connect(DB_PATH)
        cursorObject = conn.cursor()
        cursorObject.execute("INSERT INTO VideoSegDetails (FULL_FILE_PATH,DURATION,TOTALSEGS,SEGTIME,SEG_FILENAME_PATTERN,JOINSTATUS,transcoded_jobIds,outjoburis) \
                        VALUES (?,?,?,?,?,?,?,?)", (file_path, duration, totalsegs, segtime, seg_filename_pattern, 0, ' ', ' ') )
        #cursorObject.execute('COMMIT')
        conn.commit()
        conn.close

def auto_compile(path='.'):

    wm = pyinotify.WatchManager()
    # mask = pyinotify.EventsCodes.ALL_FLAGS.get('IN_CREATE', 0)
    # mask = pyinotify.EventsCodes.FLAG_COLLECTIONS['OP_FLAGS']['IN_CREATE'] 
    mask = pyinotify.IN_CLOSE_WRITE
    notifier = pyinotify.ThreadedNotifier(wm, OnIOHandler())  
    notifier.start()
    wm.add_watch(path, mask, rec=False)
    logging.info('[%s]Start monitoring %s', datetime.datetime.now(), path)
    '''
    while True:
        try:
            notifier.process_events()
            if notifier.check_events():
                notifier.read_events()
        except KeyboardInterrupt:
            notifier.stop()
            break
    '''
if __name__ == "__main__":
    auto_compile(WATCH_PATH)
    #print('monitor close')
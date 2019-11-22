# Elemental-SnS
### Warning: If you don't know what Elemental Conductor does, you probably should leave this page.
This split and stitch addon works with Elemental Conductor for acceleration of transcoding. It splits a whole video into pieces of jobs with input clippings; after all segments completes transcoding, the stitch server then joins those clips according to corresponding output profiles. 

### How to install this addon?
In order to make this addon work, we need to install the followings:
* A. Prepare dependencies:
python3, pip3
ffmpeg(this is preinstalled on Elemental Server, but is recommened to upgrade to the latest version in order to better support hevc codec), ffprobe
Sqlite3(this is installed on CentOS server)
* B. Install python modules
pip3 install pyinotify
pip3 install natsort
pip3 install chardet
* C. Create an addon work folder and a watchfolder
mkdir /data/server/addon
mkdir /data/server/cctv 
* D. Copy addon source files to addon path

### What are those addon files used for?
* split_watchfolder_v0.3.py: This script listens watchfolder using pyinotify for newly created files. Once any media file is detected, it probes video duration; based on the video length, transcoding jobs with input clipping time codes are then sent to Elemental Conductor by calling createJob_v2.py. Some information are updated to Sqlite database.
* createJob_v2.py: This script is aimed to have a Elemental Conductor job started, with predefined profile and modified parameters. It calls Elemental provided auth_curl.rb to post a job. Typical usage: python3 createJob_v2.py /data/mnt/uhd/4k.ts 00:00:00:00 00:04:00:00
* auth_curl.rb: This is Elemental official provided sample script for making a secure request. Post job usage: ./auth_curl.rb --login elemental --api-key your-key -X POST -H 'Content-type: text/xml' -d @template.xml http://serverIp/api/jobs
* template.xml: Specify a template for your own transcoding jobs. Key parts include file input, notification web call back, name_modifiers and profile Id.
* stitch_webserver_v0.3.py: Web server runs on Conductor. Whenever a job starts or completes, it is triggered to check whether all related segmentation transcoding jobs finish. If so, according to different outputs, corresponding videos segments are then been stitched using ‘ffmpeg -f concat’ command.
* config.ini: Put your parameters in this file 


### How can I use this addon?
* A. Edit config.ini and template.xml under your addon path, Save
* B. Start split watchfolder and Start stitch server (as root user):  
./restart.sh
* C. cp yourmediafile to addon watchfolder
* D. Check Elemental current transcoding jobs
* E. Once finish, run ./clear.sh when you need.
Note: tail -100f splitserver.log / stitchserver.log to monitor the ongoing jobs.
Any error occurs, please check splitserver.log, stitchserver.log, nohup-split.out and nohup-stitch.out

### What do the config.ini parameters mean?
* WATCH_PATH: addon watch folder. Throw your files here, then they will be split.
* DB_PATH: Sqlite3 DB path. One table named VideoSegDetails is used to hold split and stitch information.
* OUTPUT_FOLDER: Elemental defined outgoing folder.
* CLIPSIZE: This defines the size in seconds of each split segmentation.
* AUTH_CURL_CMD: This cmd line will be executed to fetch job details from Elemental. Replace the API key part and http server address part accordingly with your own value.
* AUTH_CURL_POST: Post a job to Elemental Conductor using this command line.
* ADDON_PATH: Path of addon source and config files.
* WEBSERVER_ADDR: The IP address of addon web server.
* WEBSERVER_PORT: The web server port that is listening to web call backs from Elemental Server or Conductor.
* TEMPLATE: Specify your job template xml file. For example, a SD transcoding job with 5 outputs has different xml from UHD transcoding job with 2 outputs.
* NO_OF_OUTPUTS: This indicates the number of outputs in template xml file.
* OUTPUT1_PREFIX: This is the indicator to differentiate group of segmented files. For example, _hevc filters all hevc codec  segmentations in order to concat corresponding video files.

### Does this addon support multiple watchfolders?
Yes. Copy python source files to different path, change config.ini parameters accordingly. Note: use different port for stitch server if these addons are running on the same host.

### Does it support multiple output?
Yes. 

### Can I repeat testing the addon with the same file?
Yes, however Elemental watchfolder is not aware of updated files with the same file names, so be sure clearing Elemental incoming and outgoing watchfolder files to make it work smoothly. You can use little script under source ‘clear.sh’ to clean.

### How can I know the total consumption time from segmentation to finish stitching?
sqlite3 DB_PATH
select Cast((julianday(jointime)-julianday(segtime))* 24 * 60 *60 As Integer) from VideoSegDetails;

### Does this addon support both Elemental Server and Conductor cluster?
Yes, make sure http connection pass through from node server to conductor server since web callback is initiated from node server.

### How can I terminate a webserver that is running?
‘ps -aux|grep python’ to get PID then kill -9 PID OR use ./restart.sh

### Do I need to restart webserver or watchfolder python programme after changing the configuration parameters?
Yes.

### How can I debug the webserver?
Under the addon folder, run
curl -X POST -H 'Content-type: text/xml' -d @req.xml http://webserverIP:8888
Change the job Id as your choice.

### Does this addon support http ABR output such as HLS, Dash, Smooth or CMAF?
Not yet, will consider adding this feature future.


## License

This library is licensed under the MIT-0 License. See the LICENSE file.

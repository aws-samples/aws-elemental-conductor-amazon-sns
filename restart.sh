ps -eaf | grep split_watchfolder | grep -v grep | awk '{ print $2 }' | xargs kill -9
ps -eaf | grep stitch_webserver | grep -v grep | awk '{ print $2 }' | xargs kill -9
nohup python3 split_watchfolder_v0.3.py &> nohup-split.out &
nohup python3 stitch_webserver_v0.3.py &> nohup-stitch.out &

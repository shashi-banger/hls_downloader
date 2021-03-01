
import m3u8
import sys
from threading import Thread
import time
import signal
from queue import Queue
from urllib.parse import urlparse
import os
import pycurl
import shlex, subprocess
#from amg_apps.mongo_db_interfaces.mongo_db_interfaces import DbInterface

class FfmpegSegmentConcatenator(Thread):
    def __init__(self, nsegments, recording_dir, collection_name=None):
        self.t = Thread.__init__(self)
        self.recording_dir = recording_dir
        self.seg_inp_q = Queue()
        self.segment_list = []
        self.num_segment_to_concat = nsegments
        self.collection_name = collection_name
        #self.db_io = DbInterface('auto_ad_mine')

    def enqueue(self, new_seg):
        self.seg_inp_q.put(new_seg)

    def close(self):
        self.seg_inp_q.put(None)
        print("calling self.seg_inp_q.join")
        self.seg_inp_q.join()
        print("finished self.seg_inp_q.join")

    def ffmpeg_concat(self):
        seg_list_fname = self.recording_dir + '/' + 'concat.txt'
        seg_list_f = open(seg_list_fname, 'w')
        for f in self.segment_list:
            seg_list_f.write("file '%s'\n" % f)
        seg_list_f.close()
        out_file = self.recording_dir + '/' + 'recording_%d.mp4' % int(time.time())
        cmd = 'ffmpeg -f concat -safe 0 -i %s -vcodec copy -acodec copy %s' %\
                                      (seg_list_fname, out_file)
        print(cmd)

        args = shlex.split(cmd)
        p = subprocess.Popen(args, stdout=subprocess.PIPE)
        o,e = p.communicate()

        #if self.collection_name != None:
        #    dic = {}
        #    dic['recording_path'] = out_file
        #    dic['extract_ad_pods'] = 0
        #    self.db_io.write_doc(self.collection_name, dic)

    def run(self):
        while True:
            seg_filename = self.seg_inp_q.get(block=True)
            if seg_filename is None:
                break
            self.segment_list.append(seg_filename)
            if len(self.segment_list) >= self.num_segment_to_concat:
                print("+++++++++++CALLING ffmpeg concat", self.num_segment_to_concat)
                self.ffmpeg_concat()
                del self.segment_list[:]
            self.seg_inp_q.task_done()
        self.seg_inp_q.task_done()



class SegmentDownloader(Thread):
    def __init__(self, download_dir, ffmpeg_concatenator):
        self.t = Thread.__init__(self)
        self.download_dir = download_dir
        self.seg_url_q = Queue()
        self.c = pycurl.Curl()
        self.ffmpeg_concatenator = ffmpeg_concatenator
        self.file_num = 0

    def enque_uri(self, uri):
        self.seg_url_q.put(uri)

    def get_q_size(self):
        return self.seg_url_q.qsize()

    def close(self):
        self.seg_url_q.put(None)
        print("calling self.seg_url_q.join")
        self.seg_url_q.join()
        print("calling self.seg_url_q.join")
        self.ffmpeg_concatenator.close()

    def __download_uri__(self, uri):
        r = urlparse(uri)
        fname = os.path.basename(r.path)
        if not fname.endswith('.ts'):
            fname = fname + '.ts'
        dest_file = self.download_dir + '/%d_' % self.file_num + fname
        #print("==============", uri, dest_file)
        self.c.setopt(self.c.URL, uri)
        out_f = open(dest_file, 'wb')
        self.c.setopt(self.c.WRITEDATA, out_f)
        self.c.setopt(self.c.FOLLOWLOCATION, True)
        self.c.setopt(pycurl.USERAGENT, 'Mozilla/5.0')
        #self.c.setopt(pycurl.VERBOSE, True)
        self.c.perform()
        self.file_num += 1
        return dest_file

    def run(self):
        while True:
            uri = self.seg_url_q.get(block=True)
            if uri is None:
                break
            seg_file = self.__download_uri__(uri)
            self.ffmpeg_concatenator.enqueue(seg_file)
            self.seg_url_q.task_done()
        self.seg_url_q.task_done()



class PlaylistReader(Thread):
    def __init__(self, pl_uri, seg_path, rec_path, nsegments, out_collection_name=None):
        self.pl_uri = pl_uri
        self.t = Thread.__init__(self)
        self.segment_uris = []
        self.max_segments = 500
        self.terminate_flag = False
        self.recorder = FfmpegSegmentConcatenator(nsegments, rec_path, out_collection_name)
        self.seg_downloader = SegmentDownloader(seg_path, self.recorder)
        self.recorder.start()
        self.seg_downloader.start()
        self.start()

    def set_pl_uri(self,uri):
        self.pl_uri = uri

    def close(self):
        self.terminate_flag = True
        self.seg_downloader.close()

    def run(self):
        while not self.terminate_flag:
            try:
                m3u8_obj = m3u8.load(self.pl_uri)
            except Exception as e:
                print(e)
                time.sleep(3)
                continue

            #print m3u8_obj.segments
            #print(m3u8_obj.playlist_type)
            for s in m3u8_obj.segments:
                # Check if the segment uri is an absolute uri
                if bool(urlparse(s.uri).netloc):
                    uri = s.uri
                else:
                    uri = s.base_uri + s.uri
                if s.uri not in self.segment_uris:
                    print(uri)
                    self.segment_uris.append(s.uri)
                    self.seg_downloader.enque_uri(uri)
                if len(self.segment_uris) > self.max_segments:
                    self.segment_uris.pop(0)
            if m3u8_obj.playlist_type == 'vod':
                print(self.seg_downloader.get_q_size())
                while self.seg_downloader.get_q_size() > 0:
                    time.sleep(s.duration)
                # All segments have been downloaded so close and break out
                self.close()
            else:
                time.sleep(s.duration)

class SigHandler(object):
    def __init__(self):
        signal.signal(signal.SIGTERM, self.terminate_sig_hndlr)
        signal.signal(signal.SIGINT, self.terminate_sig_hndlr)
        self.terminate_flag = False

    def terminate_sig_hndlr(self, signum, frame):
        print("Got terminate signal")
        self.terminate_flag = True

    def get_terminate_flag(self):
        return self.terminate_flag

'''

choose_resolution=(640,360)

m3u8_obj = m3u8.load(sys.argv[1])

chosen_p = None
print m3u8_obj.is_variant
for p in m3u8_obj.playlists:
    print p.stream_info
    print p.uri
    if p.stream_info.resolution == choose_resolution:
        chosen_p = p
        break

rec = FfmpegSegmentConcatenator('/tmp/sb1/recordings/')
sd = SegmentDownloader('/tmp/sb1/segments', rec)
pl_rdr = PlaylistReader(chosen_p.uri, sd)
rec.start()
sd.start()
pl_rdr.start()

sh = SigHandler()
while sh.get_terminate_flag() == False:
    time.sleep(5)

pl_rdr.close()
'''

'''
m3u8_pl_obj = m3u8.load(chosen_p.uri)
for s in m3u8_pl_obj.segments:
    print s.uri, s.duration
'''



import argparse
import time
import m3u8
from urllib.parse import urljoin
from hlsdownloader import PlaylistReader

class GenericDownloader(object):
    def __init__(self, inp_url, dest_seg_dir, dest_rec_dir, nsegments, collection):
        self.inp_url = inp_url
        self.dest_seg_dir = dest_seg_dir
        self.dest_rec_dir = dest_rec_dir
        self.pl_downloader = None
        p = m3u8.load(self.inp_url)
        if p.is_variant:
            dest_width = 512
            '''
            Find the nearest variant to the destination width
            '''
            nearest_v = None
            for v in p.playlists:
                if (nearest_v is None or (abs(v.stream_info.resolution[0] - dest_width) <
                    abs(nearest_v.stream_info.resolution[0] - dest_width))):
                    nearest_v = v
            if nearest_v is not None:
                print(nearest_v.stream_info)

                if not nearest_v.uri.lower().startswith('http'):
                    nearest_v.uri = urljoin(inp_url, nearest_v.uri)
                print("URI", nearest_v.uri)
                self.pl_downloader = PlaylistReader(nearest_v.uri, dest_seg_dir, dest_rec_dir, nsegments, collection)
            else:
                raise Exception("No variants in variant playlist")
        else:
            raise Exception("Input URL does not correspond to a variant playlist")



if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Record Yupp live")

    parser.add_argument('-u', '--inp_url', dest='inp_url', required=True, help='Input m3u8 url')
    parser.add_argument('-c', '--collection', dest='collection', required=False, help='Output collection where a recording entry is to be created for further processing')
    parser.add_argument('-ds', '--dest_segments_dir', dest='dest_segment_dir', required=True, help='Destination directory where the segments will be saved')
    parser.add_argument('-dr', '--dest_recording_dir', dest='dest_recording_dir', required=True, help='Destination directory where the hourly recordings will be saved')
    parser.add_argument('-n', '--nsegments', dest='nsegments', required=False, default=720, help='Number of segments to aggregate before saving concatenated segments to dest_recording_dir')

    options = parser.parse_args()

    GenericDownloader(options.inp_url, options.dest_segment_dir, options.dest_recording_dir, int(options.nsegments), options.collection)

    while True:
        time.sleep(5)



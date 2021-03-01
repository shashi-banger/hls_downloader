
# HLS downloader

A generic HLS downloader to download the segments of a particular resolution,
given an input m3u8 URL.

## Example Usage

```
 python generic_hls_downloader.py -u https://bitdash-a.akamaihd.net/content/MI201109210084_1/m3u8s/f08e80da-bf1d-4e3d-8899-f0f6155f6efa.m3u8 -ds /data/segments -dr /data/recordings/
```

## Pycurl dependencies

```
sudo apt install libcurl4-openssl-dev libssl-dev
```

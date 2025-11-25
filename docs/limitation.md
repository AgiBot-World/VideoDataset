# Limitation

## Disable B-frames of the Video Data

The video data needs to be pre-processed if B-frames are present in the video. B-frames are used to improve the quality of the video by encoding frames that are temporally related to each other. However, B-frames can cause issues in the decoding process, especially when the video is encoded with high bitrates. Therefore, it is recommended to disable B-frames before decoding.

To disable B-frames, pass `-bf 0` option to the `ffmpeg` command. For example:

```
ffmpeg -i input.mp4 -c:v libx264 -crf 23 -bf 0 output.mp4
```

## Only support limited codecs

According to <https://developer.nvidia.com/video-encode-decode-support-matrix>, videodataset focuses on the supported video codecs VP9, AV1, H.264, and H.265.

from YDStreamExtractor import getVideoInfo, setOutputCallback, overrideParam


def extract_source(url, quality=None, **params):
    for key, value in params.items():
        overrideParam(key, value)

    video_info = getVideoInfo(url, quality)

    if video_info:
        if video_info.hasMultipleStreams():
            # More than one stream found, Ask the user to select a stream
            pass

        if video_info:
            # Content Lookup needs to be disabled for dailymotion videos to work
            # if video_info.sourceName == "dailymotion":
            #     self._extra_commands["setContentLookup"] = False

            return video_info.streamURL()

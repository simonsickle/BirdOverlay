## Background
This project exists because a _good_ Owlet camera doesn't...

### What we required
For a baby monitor, we required the following:

1. Local only network support, for security
1. Support for light and dark scenes (night and day naps)
1. Supports audio
1. HomeKit Secure video for historical videos when our baby does something funny.
1. An overlay for data from our Smart Sock 3

### What we found
On the market, nothing... But a combo of available products let us do what we wanted with some work.

#### What you need
1. Owlet 3 Smart Sock (good luck buying it in the USA, thanks FDA)
1. A wyze 3 camera with starlight sensor
1. docker-wyze-bridge to get RTSP stream of the camera locally
1. gstreamer and cairo programs
1. this tool to add the owlet overlay

## Running this software
1. Grab OBS headless by using `cieg/obs-docker:latest` with docker
1. Install `rtsp-simple-server` - I recomend the docker container
1. Start running this docker container, which will publish owlet's stats as HTML
1. Point OBS's source to the RTSP stream of your camera (I use wyze, any rtsp works)
1. Add a browser source and point to this service's HTML
1. Setup the stream in OBS to point to your rtsp-simple-server instance
1. Add to scrypted/blueiris/whatever you want by using the rtsp-simple-server proxy!

## HomeKit Secure
You can add this to HKSV by using [Scrypted](https://github.com/koush/scrypted) - see that service for details. You will add this RTSP camera with the overlay as the source. A benefit of doing this is cloud recordings and AppleTV's Picture-in-Picture mode for HK cameras meaning you can watch TV and have a small image of your baby on the screen to monitor!
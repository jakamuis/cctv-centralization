FROM jrottenberg/ffmpeg:4.4-ubuntu

RUN apt-get update && apt-get install -y \
    libx264-dev \
    libx265-dev \
    libvpx-dev \
    libfdk-aac-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /streams

CMD ["ffmpeg", "-i", "input.mp4", "-c:v", "libx264", "-c:a", "aac", "-f", "hls", "-hls_time", "10", "-hls_list_size", "0", "-hls_flags", "delete_segments", "/streams/output.m3u8"]
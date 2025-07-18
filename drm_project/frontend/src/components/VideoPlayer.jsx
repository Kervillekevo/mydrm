import { useEffect, useRef, useContext } from 'react';
import videojs from 'video.js';
import 'video.js/dist/video-js.css';
import { AuthContext } from './AuthContext';

const BASE_URL = 'http://127.0.0.1:8000';

export default function VideoPlayer({ videoId }) {
  const videoRef = useRef(null);
  const { token } = useContext(AuthContext);

  useEffect(() => {
    if (!videoRef.current) return;

    // Save original XHR factory
    const originalXhr = videojs.xhr;

    // Patch it to inject headers for all HLS requests
    videojs.xhr = function (options, callback) {
      options.headers = {
        ...(options.headers || {}),
        Authorization: `Token ${token}`, // ✅ fixed template string
      };
      return originalXhr(options, callback);
    };

    const player = videojs(videoRef.current, {
      controls: true,
      autoplay: false,
      fluid: true,
    });

    player.src({
      src: `${BASE_URL}/media/videos/hls/${videoId}/720p/playlist.m3u8`, // ✅ fixed template string
      type: 'application/x-mpegURL',
    });

    return () => {
      player.dispose();
      videojs.xhr = originalXhr; // restore original XHR
    };
  }, [videoId, token]);

  return (
    <div className="my-4">
      <video ref={videoRef} className="video-js vjs-big-play-centered" playsInline />
    </div>
  );
}

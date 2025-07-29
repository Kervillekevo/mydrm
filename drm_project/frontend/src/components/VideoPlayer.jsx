import { useEffect, useRef, useState } from 'react';
import videojs from 'video.js';
import 'video.js/dist/video-js.css';
import 'videojs-contrib-quality-levels';
import HlsQualitySelector from 'videojs-hls-quality-selector';
import './VideoPlayer.css';

const BASE_URL = 'http://127.0.0.1:8000';

videojs.registerPlugin('hlsQualitySelector', function (options) {
  return new HlsQualitySelector(this, options);
});

export default function VideoPlayer({ videoId, title }) {
  const videoRef = useRef(null);
  const playerRef = useRef(null);

  const [hlsUrl, setHlsUrl] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchVideo = async () => {
      setLoading(true);
      setError(null);
      try {
        const token = localStorage.getItem('token');

        const response = await fetch(`${BASE_URL}/videos/${videoId}/`, {
          headers: token ? { Authorization: `Token ${token}` } : {},
        });

        if (!response.ok) {
          throw new Error(`Video not found (HTTP ${response.status})`);
        }

        const data = await response.json();

        if (!data.hls_url) {
          throw new Error("This video is not ready for playback yet.");
        }

        setHlsUrl(`${BASE_URL}${data.hls_url}`);
      } catch (err) {
        setError(err.message);
        setHlsUrl(null);
      } finally {
        setLoading(false);
      }
    };

    fetchVideo();
  }, [videoId]);

  useEffect(() => {
    if (!hlsUrl || !videoRef.current) return;

    if (playerRef.current) {
      playerRef.current.dispose();
    }

    const player = videojs(videoRef.current, {
      controls: true,
      preload: 'auto',
      responsive: true,
      fluid: true,
      bigPlayButton: true,
      html5: {
        vhs: {
          overrideNative: true,
          enableLowInitialPlaylist: true,
        },
      },
    });

    playerRef.current = player;

    player.src({
      src: hlsUrl,
      type: 'application/x-mpegURL',
    });

    player.ready(() => {
      try {
        player.hlsQualitySelector({ displayCurrentQuality: true });
      } catch (e) {
        console.warn('HLS quality plugin failed:', e);
      }
    });

    player.on('error', () => {
      const err = player.error();
      setError(err?.message || 'Playback error');
    });

    return () => {
      if (playerRef.current) {
        playerRef.current.dispose();
        playerRef.current = null;
      }
    };
  }, [hlsUrl]);

  return (
    <div className="video-wrapper">
      <div className="video-container">
        <div data-vjs-player>
          <video
            ref={videoRef}
            className="video-js vjs-default-skin"
            playsInline
          />
        </div>
      </div>

      {loading && (
        <div className="video-loading">Loading video...</div>
      )}

      {error && (
        <div className="video-error">
          ⚠ {error}
          <br />
          <button onClick={() => window.location.reload()} className="retry-button">
            Retry
          </button>
        </div>
      )}

      {!loading && !error && title && (
        <div className="video-meta">
          <h2 className="video-title">{title}</h2>
        </div>
      )}
    </div>
  );
}

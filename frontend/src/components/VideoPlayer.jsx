import { useEffect, useRef, useState, useCallback } from 'react';
import videojs from 'video.js';
import 'video.js/dist/video-js.css';
import 'videojs-contrib-quality-levels';
import HlsQualitySelector from 'videojs-hls-quality-selector';
import './VideoPlayer.css';

const BASE_URL = 'http://104.152.49.62';

videojs.registerPlugin('hlsQualitySelector', function(options) {
  return new HlsQualitySelector(this, options);
});

export default function VideoPlayer({ video }) {
  const videoRef = useRef(null);
  const playerRef = useRef(null);

  const [status, setStatus] = useState(video.status);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const initPlayer = (url) => {
    if (!videoRef.current) return;

    const player = videojs(videoRef.current, {
      controls: true,
      autoplay: false,
      preload: 'auto',
      responsive: true,
      fluid: true,
      html5: { vhs: { overrideNative: true } },
    });

    playerRef.current = player;

    player.src({ src: url, type: 'application/x-mpegURL' });

    player.ready(() => {
      if (!player.controlBar.getChild('QualitySelector')) {
        player.hlsQualitySelector({ displayCurrentQuality: true });
      }
    });

    player.on('error', () => {
      setError(player.error()?.message || 'Playback error');
    });

    return player;
  };

  // Initialize player with tokenized URL
  useEffect(() => {
    const token = localStorage.getItem('token');
    if (!video.hls_url) return;

    const hlsUrlWithToken = `${BASE_URL}${video.hls_url}?token=${token || ''}`;
    initPlayer(hlsUrlWithToken);

    return () => {
      if (playerRef.current) {
        playerRef.current.dispose();
        playerRef.current = null;
      }
    };
  }, [video]);

  // ✅ Poll backend for status / HLS updates
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const token = localStorage.getItem('token');
        const res = await fetch(`${BASE_URL}/videos/${video.id}/`, {
          headers: token ? { Authorization: `Token ${token}` } : {},
        });

        if (!res.ok) return;

        const data = await res.json();
        if (data.status !== status) {
          setStatus(data.status);

          if (data.hls_url && playerRef.current) {
            const player = playerRef.current;
            const currentTime = player.currentTime();
            const wasPaused = player.paused();

            const updatedUrl = `${BASE_URL}${data.hls_url}?token=${token || ''}&t=${Date.now()}`;
            player.src({ src: updatedUrl, type: 'application/x-mpegURL' });

            player.one('loadedmetadata', () => {
              player.currentTime(currentTime);
              if (!wasPaused) player.play();
            });
          }
        }
      } catch (err) {
        console.warn('Polling error:', err.message);
      }
    }, 8000);

    return () => clearInterval(interval);
  }, [video.id, status]);

  // Disable right-click context menu
  useEffect(() => {
    const videoEl = videoRef.current;
    const disableContextMenu = (e) => e.preventDefault();

    if (videoEl) videoEl.addEventListener('contextmenu', disableContextMenu);

    return () => {
      if (videoEl) videoEl.removeEventListener('contextmenu', disableContextMenu);
    };
  }, []);

  return (
    <div className="video-wrapper">
      <div className="video-container">
        <div data-vjs-player>
          <video ref={videoRef} className="video-js vjs-default-skin" playsInline />
        </div>
      </div>

      {loading && <div className="video-loading">Loading...</div>}

      {error && (
        <div className="video-error">
          ⚠ {error}
          <button onClick={() => window.location.reload()} className="retry-button">
            Retry
          </button>
        </div>
      )}

      {!loading && !error && video.title && (
        <div className="video-meta">
          <h2 className="video-title">{video.title}</h2>
        </div>
      )}
    </div>
  );
}

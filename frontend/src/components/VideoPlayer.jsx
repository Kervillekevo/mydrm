import { useEffect, useRef, useState, useCallback } from 'react';
import videojs from 'video.js';
import 'video.js/dist/video-js.css';
import 'videojs-contrib-quality-levels';
import HlsQualitySelector from 'videojs-hls-quality-selector';
import './VideoPlayer.css';

const BASE_URL = 'http://104.152.49.62';

videojs.registerPlugin('hlsQualitySelector', function (options) {
  return new HlsQualitySelector(this, options);
});

export default function VideoPlayer({ videoId, title }) {
  const videoRef = useRef(null);
  const playerRef = useRef(null);

  const [hlsUrl, setHlsUrl] = useState(null);
  const [status, setStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // ✅ Wrap fetchVideo in useCallback
  const fetchVideo = useCallback(async () => {
    try {
      const token = localStorage.getItem('token');
      const res = await fetch(`${BASE_URL}/videos/${videoId}/`, {
        headers: token ? { Authorization: `Token ${token}` } : {},
      });

      if (!res.ok) throw new Error('Video not available');

      const data = await res.json();
      if (!data.hls_url) throw new Error('HLS not ready yet');

      const fullUrl = `${BASE_URL}${data.hls_url}`;
      setHlsUrl(fullUrl);
      setStatus(data.status);
    } catch (err) {
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [videoId]);

  const initPlayer = (url) => {
    if (!videoRef.current) return;

    const player = videojs(videoRef.current, {
      controls: true,
      autoplay: false,
      preload: 'auto',
      responsive: true,
      fluid: true,
      html5: {
        vhs: {
          overrideNative: true,
        },
      },
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

  // Initial fetch
  useEffect(() => {
    fetchVideo();
  }, [fetchVideo]); // ✅ useCallback ensures stability

  // Initialize player
  useEffect(() => {
    if (hlsUrl && !playerRef.current) {
      initPlayer(hlsUrl);
    }
  }, [hlsUrl]);

  // Polling for status change
  useEffect(() => {
    const interval = setInterval(async () => {
      try {
        const token = localStorage.getItem('token');
        const res = await fetch(`${BASE_URL}/videos/${videoId}/`, {
          headers: token ? { Authorization: `Token ${token}` } : {},
        });

        if (!res.ok) return;

        const data = await res.json();
        const newStatus = data.status;

        if (newStatus !== status && data.hls_url) {
          console.log(`🔄 Status changed: ${status} → ${newStatus}`);
          setStatus(newStatus);

          const player = playerRef.current;
          if (player) {
            const currentTime = player.currentTime();
            const wasPaused = player.paused();

            const updatedUrl = `${BASE_URL}${data.hls_url}?t=${Date.now()}`;
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
  }, [videoId, status]);

  // Cleanup
  useEffect(() => {
    const videoEl = videoRef.current;
    const disableContextMenu = (e) => e.preventDefault();

    if (videoEl) videoEl.addEventListener('contextmenu', disableContextMenu);

    return () => {
      if (playerRef.current) {
        playerRef.current.dispose();
        playerRef.current = null;
      }
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

      {!loading && !error && title && (
        <div className="video-meta">
          <h2 className="video-title">{title}</h2>
        </div>
      )}
    </div>
  );
}

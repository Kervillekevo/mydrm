import { useEffect, useRef, useState, useCallback } from 'react';
import videojs from 'video.js';
import 'video.js/dist/video-js.css';
import 'videojs-contrib-quality-levels';
import HlsQualitySelector from 'videojs-hls-quality-selector';
import './VideoPlayer.css';

const BASE_URL = process.env.REACT_APP_API_BASE_URL;

videojs.registerPlugin('hlsQualitySelector', function (options) {
  return new HlsQualitySelector(this, options);
});

export default function VideoPlayer({ video }) {
  const videoRef = useRef(null);
  const playerRef = useRef(null);

  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchStreamToken = useCallback(async () => {
    const res = await fetch(`${BASE_URL}/videos/${video.id}/stream-token/`);
    if (!res.ok) throw new Error('Failed to obtain stream token');
    return (await res.text()).trim();
  }, [video.id]);

  const initPlayer = (hlsUrl) => {
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
    player.src({ src: hlsUrl, type: 'application/x-mpegURL' });

    player.ready(() => {
      if (!player.controlBar.getChild('QualitySelector')) {
        player.hlsQualitySelector({ displayCurrentQuality: true });
      }
      setLoading(false);
    });

    player.on('error', () => {
      setError(player.error()?.message || 'Playback error');
    });
  };

  useEffect(() => {
    if (!video?.id) return;

    let mounted = true;

    const startPlayback = async () => {
      try {
        const streamToken = await fetchStreamToken();
        if (!mounted) return;
        const hlsUrl = `${BASE_URL}/videos/media/${video.id}/manifest?token=${streamToken}`;
        initPlayer(hlsUrl);
      } catch (err) {
        console.error(err);
        setError('Unable to start secure playback');
        setLoading(false);
      }
    };

    startPlayback();

    return () => {
      mounted = false;
      if (playerRef.current) {
        playerRef.current.dispose();
        playerRef.current = null;
      }
    };
  }, [video?.id, fetchStreamToken]);

  useEffect(() => {
    const videoEl = videoRef.current;
    const noCtx = (e) => e.preventDefault();
    if (videoEl) videoEl.addEventListener('contextmenu', noCtx);
    return () => {
      if (videoEl) videoEl.removeEventListener('contextmenu', noCtx);
    };
  }, []);

  return (
    <div className="video-wrapper">
      <div className="video-container">
        <div data-vjs-player>
          <video ref={videoRef} className="video-js vjs-default-skin" playsInline />
        </div>
      </div>

      {loading && <div className="video-loading">Loading secure stream...</div>}

      {error && (
        <div className="video-error">
          {error}
          <button onClick={() => window.location.reload()} className="retry-button">
            Retry
          </button>
        </div>
      )}

      {!loading && !error && video?.title && (
        <div className="video-meta">
          <h2 className="video-title">{video.title}</h2>
        </div>
      )}
    </div>
  );
}
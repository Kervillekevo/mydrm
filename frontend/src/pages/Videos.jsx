import { useEffect, useState } from 'react';
import VideoPlayer from '../components/VideoPlayer';
import './Videos.css';

const BASE_URL = process.env.REACT_APP_API_BASE_URL;



export default function Videos() {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchVideos = async () => {
      try {
        const token = localStorage.getItem('token');
        const headers = token ? { Authorization: `Token ${token}` } : {};
        const res = await fetch(`${BASE_URL}/videos/`, { headers });

        if (res.status === 401) {
          localStorage.removeItem('token');
          window.location.href = '/login';
          return;
        }

        if (!res.ok) {
          console.error('Failed to fetch videos, status:', res.status);
          setVideos([]);
          return;
        }

        const data = await res.json();
        setVideos(data);
      } catch (err) {
        console.error('Error fetching videos:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchVideos();
  }, []);

  if (loading) return (
    <div className="page-container">
      <h1 className="page-title">Available Videos</h1>
      <p style={{ color: '#ccc', padding: '16px' }}>Loading videos...</p>
    </div>
  );

  if (!videos.length) return (
    <div className="page-container">
      <h1 className="page-title">Available Videos</h1>
      <p style={{ color: '#ccc', padding: '16px' }}>No videos found.</p>
    </div>
  );

  return (
    <div className="page-container">
      <h1 className="page-title">Available Videos</h1>
      <div className="video-grid">
        {videos.map(video => (
          <div key={video.id} className="video-card">
            <VideoPlayer video={video} />
          </div>
        ))}
      </div>
    </div>
  );
}

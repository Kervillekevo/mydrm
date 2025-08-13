import { useEffect, useState } from 'react';
import VideoPlayer from '../components/VideoPlayer';
import './Videos.css';

const BASE_URL = 'http://127.0.0.1:8000';

export default function Videos() {
  const [videos, setVideos] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchVideos = async () => {
      try {
        const token = localStorage.getItem('token'); // safe for both logged-in and guest
        const res = await fetch(`${BASE_URL}/videos/`, {
          headers: token ? { Authorization: `Token ${token}` } : {},
        });
        if (res.ok) {
          const data = await res.json();
          setVideos(data);
        } else {
          console.error('Failed to fetch videos');
        }
      } catch (err) {
        console.error('Error:', err);
      } finally {
        setLoading(false);
      }
    };

    fetchVideos(); // always run, regardless of login
  }, []);

  if (loading) {
    return (
      <div className="page-container">
        <h1 className="page-title">Available Videos</h1>
        <p style={{ color: '#ccc', padding: '16px' }}>Loading videos...</p>
      </div>
    );
  }

  if (!videos.length) {
    return (
      <div className="page-container">
        <h1 className="page-title">Available Videos</h1>
        <p style={{ color: '#ccc', padding: '16px' }}>No videos found.</p>
      </div>
    );
  }

  return (
    <div className="page-container">
      <h1 className="page-title">Available Videos</h1>
      <div className="video-grid">
        {videos.map((video) => (
          <div key={video.id} className="video-card">
            <VideoPlayer videoId={video.id} title={video.title} />
          </div>
        ))}
      </div>
    </div>
  );
}

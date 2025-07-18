import { useContext, useEffect, useState } from 'react';
import { AuthContext } from '../components/AuthContext';
import VideoPlayer from '../components/VideoPlayer';

const BASE_URL = 'http://127.0.0.1:8000';

export default function Videos() {
  const { token } = useContext(AuthContext);
  const [videos, setVideos] = useState([]);

  useEffect(() => {
    const fetchVideos = async () => {
      try {
        const res = await fetch(`${BASE_URL}/videos/`, {
          headers: {
            'Authorization': `Token ${token}`,
          },
        });
        if (res.ok) {
          const data = await res.json();
          setVideos(data);
        } else {
          console.error('Failed to fetch videos');
        }
      } catch (err) {
        console.error('Error:', err);
      }
    };

    if (token) {
      fetchVideos();
    }
  }, [token]);

  return (
    <div className="p-4">
      <h1 className="text-2xl font-bold mb-4">Available Videos</h1>
      {videos.map((video) => (
        <div key={video.id} className="mb-8 border-b pb-4">
          <h2 className="text-xl font-semibold">{video.title}</h2>
          <p className="text-gray-600 mb-2">{video.description}</p>
          <VideoPlayer videoId={video.id} />
        </div>
      ))}
    </div>
  );
}

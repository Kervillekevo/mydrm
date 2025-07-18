// pages/Home.jsx
import { Link } from "react-router-dom";
export default function Home() {
  return (
    <div className="main-content">
      <h1>Welcome to My DRM Platform</h1>
      <p>This is the home page.</p>

      <Link to="/videos" className="link-button">
        View Videos
      </Link>
    </div>
  );
}

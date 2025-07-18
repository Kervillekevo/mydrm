import { BrowserRouter, Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar.jsx";
import ResetPassword from "./pages/ResetPassword.jsx";
import { AuthProvider } from "./components/AuthContext.jsx";
import './App.css';
import Home from "./pages/Home.jsx";
import Videos from "./pages/Videos.jsx";
import VideoDetail from "./pages/VideoDetail.jsx";

function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Navbar />
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/reset-password/:uidb64/:token/" element={<ResetPassword />} />
          <Route path="/videos" element={<Videos/>}/>
          <Route path="/videos/:id" element={<VideoDetail/>}/>
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;

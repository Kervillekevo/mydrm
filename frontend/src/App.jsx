import { BrowserRouter, Routes, Route } from "react-router-dom";
import Navbar from "./components/Navbar.jsx";
import ResetPassword from "./pages/ResetPassword.jsx";
import { AuthProvider } from "./components/AuthContext.jsx";
import './App.css';
import Videos from "./pages/Videos.jsx";

function App() {
  return (
    <AuthProvider>
      <BrowserRouter >
        <Navbar />
        <Routes>
          
          <Route path="" element={<Videos />} />
          <Route path="videos" element={<Videos />} />
          <Route path="reset-password/:uidb64/:token" element={<ResetPassword />} />
          <Route path="*" element={<Videos />} />  
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}

export default App;

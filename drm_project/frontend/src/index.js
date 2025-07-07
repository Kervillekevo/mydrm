import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css'; // ✅ keep if you have it
import App from './App'; // ✅ this should point to YOUR App.jsx

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <App />
  </React.StrictMode>
);

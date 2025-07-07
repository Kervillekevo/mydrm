// pages/ResetPassword.jsx

import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';

const BASE_URL = 'http://127.0.0.1:8000';

export default function ResetPassword() {
  const { uid, token } = useParams();
  const navigate = useNavigate();

  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleReset = async (e) => {
    e.preventDefault();

    if (newPassword !== confirmPassword) {
      alert('Passwords do not match.');
      return;
    }

    setLoading(true);

    try {
      const res = await fetch(`${BASE_URL}/password-reset-confirm/${uid}/${token}/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          uid: uid,
          token: token,
          new_password1: newPassword,
          new_password2: confirmPassword,
        }),
      });

      const data = await res.json();
      console.log('Response status:', res.status);
      console.log('Response body:', data);

      if (res.ok) {
        alert('Password reset successful! You can now sign in.');
        navigate('/');
      } else {
        alert('Error: ' + JSON.stringify(data));
      }
    } catch (error) {
      console.error('Fetch error:', error);
      alert('Something went wrong. Check console for details.');
    } finally {
      setLoading(false);
    }
  }; 

  return (
    <div style={{ maxWidth: '400px', margin: '50px auto' }}>
      <h2>Reset Your Password</h2>
      <form onSubmit={handleReset}>
        <input
          type="password"
          placeholder="New Password"
          value={newPassword}
          required
          onChange={(e) => setNewPassword(e.target.value)}
        />
        <input
          type="password"
          placeholder="Confirm New Password"
          value={confirmPassword}
          required
          onChange={(e) => setConfirmPassword(e.target.value)}
        />
        <button type="submit" disabled={loading}>
          {loading ? 'Resetting...' : 'Reset Password'}
        </button>
      </form>
    </div>
  );
}  
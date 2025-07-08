// ✅ pages/ResetPassword.jsx

import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';

const BASE_URL = 'http://127.0.0.1:8000';

export default function ResetPassword() {
  // ✅ Must match Django URL pattern: <uidb64>/<token>/
  const { uidb64, token } = useParams();
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
const response = await fetch(
  `${BASE_URL}/password-reset-confirm/${uidb64}/${token}/`,
  {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      password: newPassword,
      token: token,      // ✅ Include it here
      uidb64: uidb64,    // ✅ Include it here too
    }),
  }
);


      const data = await response.json();
      console.log('Status:', response.status);
      console.log('Data:', data);

      if (response.ok) {
        alert('✅ Password reset successful! Please log in.');
        navigate('/login');
      } else {
        alert('❌ Error: ' + (data.error || JSON.stringify(data)));
      }
    } catch (error) {
      console.error('Fetch error:', error);
      alert('Something went wrong. Please try again.');
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

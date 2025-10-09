import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import './ResetPassword.css';

const BASE_URL = 'http://104.152.49.62';

export default function ResetPassword() {
  const { uidb64, token } = useParams();
  const navigate = useNavigate();

  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [showNewPassword, setShowNewPassword] = useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = useState(false);

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
            token: token,
            uidb64: uidb64,
          }),
        }
      );

      const data = await response.json();

      if (response.ok) {
        alert('✅ Password reset successful! Please log in.');
        navigate('/login');
      } else {
        alert('❌ Error: ' + (data.error || JSON.stringify(data)));
      }
    } catch (error) {
      alert('Something went wrong. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
   <div className="reset-page-wrapper">
    <div className="reset-password-container">
      <h2 className="reset-title">Reset Your Password</h2>
      <form className="reset-form" onSubmit={handleReset}>

        {/* New Password */}
        <div className="password-field">
          <input
            className="reset-input"
            type={showNewPassword ? 'text' : 'password'}
            placeholder="New Password"
            value={newPassword}
            required
            onChange={(e) => setNewPassword(e.target.value)}
          />
          <span
            className="toggle-visibility"
            onClick={() => setShowNewPassword(!showNewPassword)}
          >
            {showNewPassword ? '🙈' : '👁'}
          </span>
        </div>

        {/* Confirm Password */}
        <div className="password-field">
          <input
            className="reset-input"
            type={showConfirmPassword ? 'text' : 'password'}
            placeholder="Confirm New Password"
            value={confirmPassword}
            required
            onChange={(e) => setConfirmPassword(e.target.value)}
          />
          <span
            className="toggle-visibility"
            onClick={() => setShowConfirmPassword(!showConfirmPassword)}
          >
            {showConfirmPassword ? '🙈' : '👁'}
          </span>
        </div>

        <button className="reset-button" type="submit" disabled={loading}>
          {loading ? 'Resetting...' : 'Reset Password'}
        </button>
      </form>
    </div>
    </div>
  );
}

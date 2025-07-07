import { useContext, useState } from 'react';
import { AuthContext } from './AuthContext';
import './Navbar.css';

export default function Navbar() {
  const { user, signIn, signOut, signUp, requestPasswordReset } = useContext(AuthContext);

  const [showModal, setShowModal] = useState(false);
  const [isSignUp, setIsSignUp] = useState(false);
  const [isReset, setIsReset] = useState(false); // NEW

  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  const handleSignIn = async (e) => {
    e.preventDefault();
    await signIn(username, password);
    setShowModal(false);
    resetForm();
  };

  const handleSignUp = async (e) => {
    e.preventDefault();
    await signUp(username, email, password);
    setIsSignUp(false);
    resetForm();
  };

  const handleReset = async (e) => {
    e.preventDefault();
    if (!email) {
      alert('Please enter your email.');
      return;
    }
    await requestPasswordReset(email);
    alert('If your email exists, a reset link has been sent.');
    setIsReset(false);
    resetForm();
  };

  const resetForm = () => {
    setUsername('');
    setEmail('');
    setPassword('');
  };

  return (
    <nav className="navbar">
      <div className="logo">MYDRM</div>
      <div className="nav-actions">
        {user ? (
          <button onClick={signOut} className="nav-btn">Sign Out</button>
        ) : (
          <button onClick={() => setShowModal(true)} className="nav-btn">Sign In</button>
        )}
      </div>

      {showModal && (
        <div className="modal">
          <form
            className="modal-content"
            onSubmit={
              isReset
                ? handleReset
                : isSignUp
                  ? handleSignUp
                  : handleSignIn
            }
          >
            <h2>
              {isReset ? 'Reset Password' : isSignUp ? 'Sign Up' : 'Sign In'}
            </h2>

            {!isReset && (
              <input
                type="text"
                placeholder="Username"
                value={username}
                required
                onChange={(e) => setUsername(e.target.value)}
              />
            )}

            {(isSignUp || isReset) && (
              <input
                type="email"
                placeholder="Email"
                value={email}
                required
                onChange={(e) => setEmail(e.target.value)}
              />
            )}

            {!isReset && (
              <input
                type="password"
                placeholder="Password"
                value={password}
                required
                onChange={(e) => setPassword(e.target.value)}
              />
            )}

            <button type="submit">
              {isReset ? 'Send Reset Link' : isSignUp ? 'Register' : 'Sign In'}
            </button>

            {!isReset && (
              <>
                <p>
                  {isSignUp ? (
                    <>
                      Already have an account?{' '}
                      <span className="link" onClick={() => setIsSignUp(false)}>Sign In</span>
                    </>
                  ) : (
                    <>
                      No account?{' '}
                      <span className="link" onClick={() => setIsSignUp(true)}>Sign Up</span>
                    </>
                  )}
                </p>
                <p>
                  <span className="link" onClick={() => {
                    setIsReset(true);
                    setIsSignUp(false);
                    resetForm();
                  }}>
                    Forgot Password?
                  </span>
                </p>
              </>
            )}

            {isReset && (
              <p>
                <span className="link" onClick={() => {
                  setIsReset(false);
                  resetForm();
                }}>
                  Back to Sign In
                </span>
              </p>
            )}

            <button type="button" onClick={() => {
              setShowModal(false);
              setIsReset(false);
              setIsSignUp(false);
              resetForm();
            }}>
              Close
            </button>
          </form>
        </div>
      )}
    </nav>
  );
}

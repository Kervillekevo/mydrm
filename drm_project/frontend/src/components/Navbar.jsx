import { useContext, useState } from 'react';
import { AuthContext } from './AuthContext';
import './Navbar.css';

export default function Navbar() {
  const { user, signIn, signUp, signOut, requestPasswordReset, updateProfile, reloadProfile } = useContext(AuthContext);

 
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [isSignUp, setIsSignUp] = useState(false);
  const [isReset, setIsReset] = useState(false);
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showProfileModal, setShowProfileModal] = useState(false);
  const [bio, setBio] = useState('');
  const [phone, setPhone] = useState('');
  const [profilePhotoFile, setProfilePhotoFile] = useState(null);
  const [removePhoto, setRemovePhoto] = useState(false);

  const resetAuthForm = () => {
    setUsername('');
    setEmail('');
    setPassword('');
    setIsSignUp(false);
    setIsReset(false);
  };

  const handleSignIn = async (e) => {
    e.preventDefault();
    await signIn(username, password);
    setShowAuthModal(false);
    resetAuthForm();
  };

  const handleSignUp = async (e) => {
    e.preventDefault();
    await signUp(username, email, password);
    setIsSignUp(false);
    resetAuthForm();
  };

  const handleReset = async (e) => {
    e.preventDefault();
    await requestPasswordReset(email);
    alert('If the email exists, a reset link has been sent.');
    setIsReset(false);
    resetAuthForm();
  };

  const handleOpenProfileModal = () => {
    if (user) {
      setBio(user.bio || '');
      setPhone(user.phone || '');
      setProfilePhotoFile(null);
      setRemovePhoto(false);
    }
    setShowProfileModal(true);
  };

  const handleSaveProfile = async () => {
    try {
      await updateProfile({
        bio: bio,
        phone: phone,
        profile_photo: profilePhotoFile,
        removePhoto: removePhoto,
      });

      
      await reloadProfile();

      alert('Profile updated!');
      setShowProfileModal(false);
    } catch (err) {
      console.error(err);
      alert('Failed to update profile.');
    }
  };

  return (
    <>
      <header className="header">
        <div className="logo">MYDRM</div>
        <div className="header-actions">
          {user?.profile_photo ? (
            <img
              src={user.profile_photo}
              alt="Profile"
              className="header-avatar"
              onClick={handleOpenProfileModal}
              style={{ cursor: 'pointer' }}
            />
          ) : user ? (
            <span
              className="header-avatar"
              onClick={handleOpenProfileModal}
              style={{ cursor: 'pointer' }}
            >
              No Photo
            </span>
          ) : null}

          {user ? (
            <button onClick={signOut} className="header-btn">Sign Out</button>
          ) : (
            <button onClick={() => setShowAuthModal(true)} className="header-btn">Sign In</button>
          )}
        </div>
      </header>

      
      {showAuthModal && (
        <div className="modal">
          <form
            className="modal-content"
            onSubmit={isReset ? handleReset : isSignUp ? handleSignUp : handleSignIn}
          >
            <h2>{isReset ? 'Reset Password' : isSignUp ? 'Sign Up' : 'Sign In'}</h2>

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
                    <>Already have an account?{' '}
                      <span className="link" onClick={() => setIsSignUp(false)}>Sign In</span></>
                  ) : (
                    <>No account?{' '}
                      <span className="link" onClick={() => setIsSignUp(true)}>Sign Up</span></>
                  )}
                </p>
                <p>
                  <span className="link" onClick={() => { setIsReset(true); setIsSignUp(false); }}>Forgot Password?</span>
                </p>
              </>
            )}

            {isReset && (
              <p><span className="link" onClick={() => setIsReset(false)}>Back to Sign In</span></p>
            )}

            <button type="button" className="close-btn" onClick={() => setShowAuthModal(false)}>Close</button>
          </form>
        </div>
      )}

    
      {showProfileModal && user && (
        <div className="modal">
          <div className="modal-content">
            <h2>Edit Profile</h2>

            {user.profile_photo && !removePhoto ? (
              <>
                <img
                  src={user.profile_photo}
                  alt="Profile"
                  style={{ width: '100px', height: '100px', borderRadius: '50%' }}
                />
                <button onClick={() => setRemovePhoto(true)}>Remove Current Photo</button>
              </>
            ) : (
              <p>No profile photo</p>
            )}

            <label>Upload New Photo:</label>
            <input
              type="file"
              accept="image/*"
              onChange={(e) => {
                setProfilePhotoFile(e.target.files[0]);
                setRemovePhoto(false);
              }}
            />

            <p><strong>Username:</strong> {user.username}</p>
            <p><strong>Email:</strong> {user.email}</p>

            <label>Bio:</label>
            <textarea value={bio} onChange={(e) => setBio(e.target.value)} />

            <label>Phone:</label>
            <input type="text" value={phone} onChange={(e) => setPhone(e.target.value)} />

            <button onClick={handleSaveProfile}>Save</button>
            <button onClick={() => setShowProfileModal(false)}>Cancel</button>
          </div>
        </div>
      )}
    </>
  );
}

import { createContext, useState, useEffect } from 'react';

export const AuthContext = createContext();

const BASE_URL = process.env.REACT_APP_API_BASE_URL;



export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(() => {
    const savedToken = localStorage.getItem('token');
    return savedToken && savedToken !== '' ? savedToken : null;
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {

    const fetchProfile = async () => {
      if (!token) {
        setUser(null);
        setLoading(false);
        return;
      }

      try {
        const res = await fetch(`${BASE_URL}/profile/`, {
          headers: {
            'Authorization': `Token ${token}`,
          },
        });

        if (res.ok) {
          const data = await res.json();
          setUser(data);
          console.log('✅ Profile loaded successfully');
        } else {
          // Clear invalid token
          console.log('❌ Invalid token, clearing authentication...');
          setUser(null);
          setToken(null);
          localStorage.removeItem('token');
        }
      } catch (error) {
        console.error('Profile fetch error:', error);
        setUser(null);
        // Don't clear token on network errors, only on auth errors
      } finally {
        setLoading(false);
      }
    };

    fetchProfile();
  }, [token]);

  const signIn = async (username, password) => {
    try {
      const res = await fetch(`${BASE_URL}/login/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
        credentials: "omit",
      });

      if (res.ok) {
        const data = await res.json();
        const authToken = data.token;

        setToken(authToken);
        localStorage.setItem('token', authToken);
        console.log('✅ Login successful');
      } else {
        alert('Invalid credentials');
      }
    } catch (error) {
      console.error('Login error:', error);
      alert('Login failed. Please try again.');
    }
  };

  const signUp = async (username, email, password) => {
    try {
      const res = await fetch(`${BASE_URL}/register/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, email, password }),
      });

      if (res.ok) {
        alert('Registered successfully! Please sign in.');
      } else {
        alert('Registration failed.');
      }
    } catch (error) {
      console.error('Registration error:', error);
      alert('Registration failed. Please try again.');
    }
  };

  const signOut = async () => {
    try {
      if (token) {
        await fetch(`${BASE_URL}/logout/`, {
          method: 'POST',
          headers: {
            'Authorization': `Token ${token}`,
          },
        });
      }
    } catch (error) {
      console.error('Logout error:', error);
    } finally {
      // Always clear local state regardless of server response
      localStorage.removeItem('token');
      setToken(null);
      setUser(null);
      console.log('✅ Logged out successfully');
    }
  };

  const updateProfile = async ({ bio, phone, profile_photo, removePhoto }) => {
    if (!token) {
      alert('Please log in to update your profile.');
      return false;
    }

    try {
      const formData = new FormData();
      formData.append('bio', bio || '');
      formData.append('phone', phone || '');

      if (removePhoto) {
        formData.append('remove_photo', 'true');
      } else if (profile_photo) {
        formData.append('profile_photo', profile_photo);
      }

      const res = await fetch(`${BASE_URL}/profile/`, {
        method: 'PATCH',
        headers: {
          'Authorization': `Token ${token}`,
        },
        body: formData,
      });

      if (res.ok) {
        const updatedProfile = await res.json();
        setUser(updatedProfile);
        return true;
      } else {
        console.error(await res.text());
        alert('Failed to update profile.');
        return false;
      }
    } catch (error) {
      console.error('Profile update error:', error);
      alert('Failed to update profile. Please try again.');
      return false;
    }
  };

  const requestPasswordReset = async (email) => {
    try {
      console.log('Sending email:', email);
      const res = await fetch(`${BASE_URL}/password-reset/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });

      const result = await res.text();
      console.log('Status:', res.status);
      console.log('Response:', result);

      if (res.ok) {
        alert('Password reset link sent. Check your email.');
      } else {
        alert('Error sending reset link.');
      }
    } catch (error) {
      console.error('Password reset error:', error);
      alert('Error sending reset link. Please try again.');
    }
  };

  const passwordResetConfirm = async (uidb64, tokenValue, password) => {
    try {
      const res = await fetch(`${BASE_URL}/password-reset-confirm/${uidb64}/${tokenValue}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ password }),
      });

      if (res.ok) {
        alert('Password reset successful. Please log in.');
      } else {
        alert('Password reset failed.');
      }
    } catch (error) {
      console.error('Password reset confirm error:', error);
      alert('Password reset failed. Please try again.');
    }
  };

  const reloadProfile = async () => {
    if (!token) {
      setUser(null);
      return;
    }

    try {
      const res = await fetch(`${BASE_URL}/profile/`, {
        headers: { 'Authorization': `Token ${token}` },
      });
      
      if (res.ok) {
        const data = await res.json();
        setUser(data);
      } else {
        setUser(null);
        // If profile reload fails, token might be invalid
        if (res.status === 401) {
          setToken(null);
          localStorage.removeItem('token');
        }
      }
    } catch (error) {
      console.error('Profile reload error:', error);
      setUser(null);
    }
  };

  // Helper function to check if user is authenticated
  const isAuthenticated = () => {
    return !!(token && user);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        loading,
        isAuthenticated,
        signIn,
        signUp,
        signOut,
        updateProfile,
        requestPasswordReset,
        passwordResetConfirm,
        reloadProfile,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
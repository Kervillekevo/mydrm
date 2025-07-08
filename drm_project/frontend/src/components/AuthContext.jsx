import { createContext, useState, useEffect } from 'react';

export const AuthContext = createContext();

const BASE_URL = "http://127.0.0.1:8000";

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [token, setToken] = useState(() => localStorage.getItem('token') || '');

 
  useEffect(() => {
    const fetchProfile = async () => {
      if (!token) {
        setUser(null);
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
        } else {
          setUser(null);
        }
      } catch (error) {
        console.error('Profile fetch error:', error);
        setUser(null);
      }
    };

    fetchProfile();
  }, [token]); 

  const signIn = async (username, password) => {
    const res = await fetch(`${BASE_URL}/login/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ username, password }),
    });

    if (res.ok) {
      const data = await res.json();
      const authToken = data.token;

     
      setToken(authToken);
      localStorage.setItem('token', authToken);

      
    } else {
      alert('Invalid credentials');
    }
  };

  const signUp = async (username, email, password) => {
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
  };

  const signOut = async () => {
    await fetch(`${BASE_URL}/logout/`, {
      method: 'POST',
      headers: {
        'Authorization': `Token ${token}`,
      },
    });

    localStorage.removeItem('token');
    setToken('');
    setUser(null);
  };

  const updateProfile = async ({ bio, phone, profile_photo, removePhoto }) => {
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
  };

 const requestPasswordReset = async (email) => {
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
};


  const passwordResetConfirm = async (uidb64, tokenValue, password) => {
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
  };

  
const reloadProfile = async () => {
  if (!token) {
    setUser(null);
    return;
  }
  const res = await fetch(`${BASE_URL}/profile/`, {
    headers: { 'Authorization': `Token ${token}` },
  });
  if (res.ok) {
    const data = await res.json();
    setUser(data);
  } else {
    setUser(null);
  }
};

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
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

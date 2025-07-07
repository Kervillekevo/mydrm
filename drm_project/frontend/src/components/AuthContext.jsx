
import { createContext, useState, useEffect } from 'react';


const BASE_URL = "http://127.0.0.1:8000";

export const AuthContext = createContext();
await fetch("http://127.0.0.1:8000/csrf/", {
  credentials: "include",
});


export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);

  useEffect(() => {
    const fetchProfile = async () => {
      const res = await fetch(`${BASE_URL}/profile/`, {
        credentials: 'include',
      });
      if (res.ok) {
        const data = await res.json();
        setUser(data);
      } else {
        setUser(null);
      }
    };
    fetchProfile();
  }, []);

  const signIn = async (username, password) => {
    const res = await fetch(`${BASE_URL}/login/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ username, password }),
    });
    if (res.ok) {
      const profileRes = await fetch(`${BASE_URL}/profile/`, {
        credentials: 'include',
      });
      const profileData = await profileRes.json();
      setUser(profileData);
    } else {
      alert('Invalid credentials');
    }
  };

  const signUp = async (username, email, password) => {
    const res = await fetch(`${BASE_URL}/register/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
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
      credentials: 'include',
    });
    setUser(null);
  };

  const requestPasswordReset = async (email) => {
    const res = await fetch(`${BASE_URL}/password-reset/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email }),
    });
    if (res.ok) {
      alert('Password reset link sent. Check your email.');
    } else {
      alert('Error sending reset link.');
    }
  };

  const passwordResetConfirm = async (uidb64, token, password) => {
  const res = await fetch(`${BASE_URL}/password-reset-confirm/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      uidb64,
      token,
      password,
    }),
  });

  if (res.ok) {
    alert('Password reset successful. Please log in.');
  } else {
    alert('Password reset failed.');
  }
};


  return (
    <AuthContext.Provider value={{ user, signIn, signUp, signOut, requestPasswordReset, passwordResetConfirm }}>
      {children}
    </AuthContext.Provider>
  );
}



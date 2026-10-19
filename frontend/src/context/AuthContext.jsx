import { useEffect, useState } from 'react';
import { AuthContext } from './authContextInstance';
import { authService } from '../services/authService';

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => authService.getCurrentUser());
  const [token, setToken] = useState(() => authService.getToken());
  const [loading, setLoading] = useState(() => Boolean(authService.getToken()));

  useEffect(() => {
    // If token exists, verify session with backend
    if (token) {
      authService
        .getMe()
        .then((userData) => {
          setUser(userData);
        })
        .catch(() => {
          // Token expired or invalid
          authService.logout();
          setUser(null);
          setToken(null);
        })
        .finally(() => setLoading(false));
    }

    const handleAuthExpired = () => {
      setUser(null);
      setToken(null);
      setLoading(false);
    };

    window.addEventListener('auth:expired', handleAuthExpired);
    return () => window.removeEventListener('auth:expired', handleAuthExpired);
  }, [token]);

  const register = async (payload) => {
    const data = await authService.register(payload);
    if (data?.access_token) {
      setToken(data.access_token);
      setUser(data.user);
    }
    return data;
  };

  const login = async (username, password) => {
    const data = await authService.login(username, password);
    setToken(data.access_token);
    setUser(data.user);
    return data;
  };

  const logout = () => {
    authService.logout();
    setToken(null);
    setUser(null);
  };

  const deleteAccount = async (password) => {
    const res = await authService.deleteAccount(password);
    setToken(null);
    setUser(null);
    return res;
  };

  const value = {
    user,
    token,
    isAuthenticated: Boolean(token),
    register,
    login,
    logout,
    deleteAccount,
    loading,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

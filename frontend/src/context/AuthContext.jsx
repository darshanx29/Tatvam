import React, { createContext, useContext, useState, useEffect } from 'react';
import { api, setCsrfToken } from '../api';

const AuthContext = createContext(null);

export const INSTITUTION = 'institution_admin';
export const SCRUTINY = 'scrutiny_officer';
export const VERIFIER = 'verification_officer';
export const ADMIN = 'system_admin';
export const OFFICERS = [SCRUTINY, VERIFIER];

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  const refreshUser = async () => {
    try {
      const data = await api.getMe();
      if (data && data.authenticated && data.user) {
        setUser(data.user);
        if (data.csrf_token) setCsrfToken(data.csrf_token);
      } else {
        setUser(null);
        if (data && data.csrf_token) setCsrfToken(data.csrf_token);
      }
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshUser();
  }, []);

  const login = async (email, password) => {
    const res = await api.login(email, password);
    setUser(res.user);
    return res;
  };

  const logout = async () => {
    try {
      await api.logout();
    } finally {
      setUser(null);
      window.location.hash = '#/login';
    }
  };

  const isOfficer = user && OFFICERS.includes(user.role);
  const isAdmin = user && user.role === ADMIN;
  const isInstitution = user && user.role === INSTITUTION;

  return (
    <AuthContext.Provider value={{ user, loading, login, logout, refreshUser, isOfficer, isAdmin, isInstitution }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider');
  return ctx;
}

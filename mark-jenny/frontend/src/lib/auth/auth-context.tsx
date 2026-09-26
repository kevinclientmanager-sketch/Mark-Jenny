"use client";

import { createContext, useContext, useState, useEffect, ReactNode } from "react";
import { api } from "../api";

interface User {
  id: number;
  email: string;
  full_name: string | null;
  avatar_url: string | null;
  role: string;
  is_active: boolean;
  is_verified: boolean;
  created_at: string;
  last_login_at: string | null;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, full_name?: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshUser: () => Promise<void>;
}

// TEMPORARY: auto-login so the UI opens directly without the login screen.
// Set enabled: false to restore full authentication (login required).
const AUTO_LOGIN_DEMO = {
  enabled: false,
  email: "kevin.clientmanager@gmail.com",
  password: "Admin1234",
};

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchAccessToken = async (email: string, password: string) => {
    const API_BASE = process.env.NEXT_PUBLIC_API_URL || '/api/v1';
    const formData = new URLSearchParams();
    formData.append('username', email);
    formData.append('password', password);

    const res = await fetch(`${API_BASE}/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      body: formData.toString(),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({ detail: 'Login failed' }));
      throw new Error(err.detail || 'Login failed');
    }

    const response = await res.json();
    localStorage.setItem('access_token', response.access_token);
    localStorage.setItem('refresh_token', response.refresh_token);
  };

  const refreshUser = async () => {
    let token = localStorage.getItem('access_token');
    if (!token && AUTO_LOGIN_DEMO.enabled) {
      try {
        await fetchAccessToken(AUTO_LOGIN_DEMO.email, AUTO_LOGIN_DEMO.password);
        token = localStorage.getItem('access_token');
      } catch {
        token = null;
      }
    }

    if (!token) {
      setUser(null);
      setLoading(false);
      return;
    }

    try {
      const userData = await api.get<User>('/auth/me');
      setUser(userData);
    } catch (err) {
      // Stored token is dead (expired/invalid) — try a fresh auto-login before giving up
      if (AUTO_LOGIN_DEMO.enabled) {
        try {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          await fetchAccessToken(AUTO_LOGIN_DEMO.email, AUTO_LOGIN_DEMO.password);
          const userData = await api.get<User>('/auth/me');
          setUser(userData);
          return;
        } catch {
          // fall through to logged-out state
        }
      }
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshUser();
  }, []);

  const login = async (email: string, password: string) => {
    await fetchAccessToken(email, password);
    await refreshUser();
  };

  const register = async (email: string, password: string, full_name?: string) => {
    await api.post('/auth/register', { email, password, full_name });
    await login(email, password);
  };

  const logout = async () => {
    try {
      await api.post('/auth/logout', {});
    } catch (err) {
      console.error(err);
    } finally {
      localStorage.removeItem('access_token');
      localStorage.removeItem('refresh_token');
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout, refreshUser }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}

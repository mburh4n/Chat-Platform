import { createContext } from "react";

// Kept in its own file so AuthProvider.jsx only exports a component
// (required for Vite's fast refresh)
export const AuthContext = createContext(null);

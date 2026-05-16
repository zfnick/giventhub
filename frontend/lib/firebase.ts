import { initializeApp, getApps, getApp } from "firebase/app";
import { getAuth, GoogleAuthProvider } from "firebase/auth";

const firebaseConfig = {
  apiKey: process.env.NEXT_PUBLIC_FIREBASE_API_KEY || "AIzaSyAdivXciSrzII6lWG2SVeYsSr_-b3t9IIs",
  authDomain: process.env.NEXT_PUBLIC_FIREBASE_AUTH_DOMAIN || "ninth-library-496500-d8.firebaseapp.com",
  projectId: process.env.NEXT_PUBLIC_FIREBASE_PROJECT_ID || "ninth-library-496500-d8",
  storageBucket: process.env.NEXT_PUBLIC_FIREBASE_STORAGE_BUCKET || "ninth-library-496500-d8.firebasestorage.app",
  messagingSenderId: process.env.NEXT_PUBLIC_FIREBASE_MESSAGING_SENDER_ID || "1009420638811",
  appId: process.env.NEXT_PUBLIC_FIREBASE_APP_ID || "1:1009420638811:web:d1eb9b77fef2f0fe50fd7e"
};

const app = !getApps().length ? initializeApp(firebaseConfig) : getApp();
const auth = getAuth(app);
const googleProvider = new GoogleAuthProvider();

// Full CRUD — Google Workspace suite
googleProvider.addScope("https://www.googleapis.com/auth/drive");
googleProvider.addScope("https://www.googleapis.com/auth/documents");
googleProvider.addScope("https://www.googleapis.com/auth/spreadsheets");
googleProvider.addScope("https://www.googleapis.com/auth/presentations");
googleProvider.addScope("https://www.googleapis.com/auth/forms.body");
googleProvider.addScope("https://www.googleapis.com/auth/forms.responses.readonly");
googleProvider.addScope("https://mail.google.com/");
googleProvider.addScope("https://www.googleapis.com/auth/calendar");
googleProvider.addScope("https://www.googleapis.com/auth/admin.directory.user");

export { app, auth, googleProvider };

"use client";

import React, { useState, useEffect } from "react";
import { onAuthStateChanged } from "firebase/auth";
import { auth } from "../../firebase/firebase.init";
import LoginView from "../components/LoginView";
import DashboardLayout from "../components/DashboardLayout";

export default function Home() {
  const [userProfile, setUserProfile] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (firebaseUser) => {
      if (firebaseUser) {
        const stored = localStorage.getItem(`cashscope_profile_${firebaseUser.uid}`);
        if (stored) {
          setUserProfile(JSON.parse(stored));
        } else {
          setUserProfile({
            uid: firebaseUser.uid,
            name: "Field Officer",
            phone: firebaseUser.phoneNumber || "Unknown",
            language: "English",
            division: "Dhaka",
            district: "Dhaka"
          });
        }
      } else {
        setUserProfile(null);
      }
      setAuthLoading(false);
    });

    return () => unsubscribe();
  }, []);

  if (authLoading) {
    return (
      <div className="min-h-screen bg-background flex flex-col items-center justify-center font-sans">
        <div className="relative flex flex-col items-center">
          <div className="w-16 h-16 rounded-full border-4 border-slate-100 border-t-secondary animate-spin"></div>
          <p className="mt-4 text-sm font-semibold text-heading animate-pulse">
            Verifying secure session...
          </p>
        </div>
      </div>
    );
  }

  if (!userProfile) {
    return <LoginView onLoginSuccess={(profile) => setUserProfile(profile)} />;
  }

  return <DashboardLayout userProfile={userProfile} />;
}

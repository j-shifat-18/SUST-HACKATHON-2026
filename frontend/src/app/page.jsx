"use client";

import React, { useState, useEffect } from "react";
import { onAuthStateChanged } from "firebase/auth";
import { auth } from "../../firebase/firebase.init";
import LoginView from "../components/LoginView";
import DashboardLayout from "../components/DashboardLayout";
import { API_BASE_URL } from "../config";

export default function Home() {
  const [userProfile, setUserProfile] = useState(null);
  const [authLoading, setAuthLoading] = useState(true);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      if (firebaseUser) {
        let profile = null;
        try {
          const idToken = await firebaseUser.getIdToken();
          const response = await fetch(`${API_BASE_URL}/api/v1/users?phone=${encodeURIComponent(firebaseUser.phoneNumber)}`, {
            headers: {
              "Authorization": `Bearer ${idToken}`
            }
          });
          if (response.ok) {
            const data = await response.json();
            const matchedUser = Array.isArray(data)
              ? data.find(u => String(u.phone).replace(/\D/g, "").slice(-10) === String(firebaseUser.phoneNumber).replace(/\D/g, "").slice(-10))
              : data;
            if (matchedUser) {
              profile = {
                uid: firebaseUser.uid,
                name: matchedUser.name,
                phone: matchedUser.phone,
                language: matchedUser.language || "English",
                division: matchedUser.region,
                district: matchedUser.area
              };
            }
          }
        } catch (apiErr) {
          console.error("Failed to fetch session profile from backend:", apiErr);
        }

        if (profile) {
          setUserProfile(profile);
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

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
    if (!auth) {
      setAuthLoading(false);
      return;
    }

    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      if (firebaseUser) {
        let profile = null;
        try {
          const idToken = await firebaseUser.getIdToken();
          const response = await fetch(
            `http://localhost:8000/api/v1/users?phone=${encodeURIComponent(firebaseUser.phoneNumber)}`,
            { headers: { Authorization: `Bearer ${idToken}` } }
          );
          if (response.ok) {
            const data = await response.json();
            const matchedUser = Array.isArray(data)
              ? data.find(
                  (u) =>
                    String(u.phone).replace(/\D/g, "").slice(-10) ===
                    String(firebaseUser.phoneNumber).replace(/\D/g, "").slice(-10)
                )
              : data;
            if (matchedUser) {
              profile = {
                uid: firebaseUser.uid,
                id: matchedUser.id,
                name: matchedUser.name,
                phone: matchedUser.phone,
                language: matchedUser.language || "English",
                division: matchedUser.region,
                district: matchedUser.area,
                role: matchedUser.role,
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
            district: "Dhaka",
            role: "operator",
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
          <div className="w-14 h-14 rounded-full border-4 border-surface-elevated border-t-primary animate-spin"></div>
          <p className="mt-4 text-sm font-medium text-muted-custom animate-pulse">
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

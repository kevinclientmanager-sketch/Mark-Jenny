"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
export default function AdvancedFeaturesPage() { const r = useRouter(); useEffect(()=>{r.replace("/settings")},[r]); return null; }

"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
export default function AdvancedPage() { const r = useRouter(); useEffect(()=>{r.replace("/settings")},[r]); return null; }

"use client";
import { useEffect } from "react";
import { useRouter } from "next/navigation";
export default function MemoryPage() { const r = useRouter(); useEffect(()=>{r.replace("/knowledge")},[r]); return null; }

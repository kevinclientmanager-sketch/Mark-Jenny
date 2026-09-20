import { redirect } from "next/navigation";

export default function BrowserPage() {
  redirect("/chat?mode=browse");
}

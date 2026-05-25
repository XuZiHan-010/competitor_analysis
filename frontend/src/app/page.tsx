import { redirect } from "next/navigation";

export default function Home() {
  // Stage 1: the only real entry is the new-task wizard. Stage 2 will swap
  // this for a marketing landing or "my reports" depending on auth state.
  redirect("/tasks/new");
}

import { createClient } from "@/lib/supabase/server";

export async function AuthButton() {
  const supabase = await createClient();
  await supabase.auth.getSession();

  return null;
}

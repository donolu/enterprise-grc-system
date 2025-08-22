import { useQuery } from "@tanstack/react-query";
import api from "@/lib/api";

// This is a placeholder. We'll need to implement the /api/me endpoint in Django.
const fetchMe = async () => {
    // const { data } = await api.get("/auth/me/");
    // return data;
    return { email: "test@example.com", roles: ["admin"] }; // Placeholder
}

export function useMe() {
  return useQuery({
    queryKey: ["me"],
    queryFn: fetchMe,
    retry: false,
  });
}

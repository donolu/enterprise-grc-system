"use client";
import { useMe } from "@/hooks/useMe";
import { useEffect } from "react";
import { useRouter } from "next/navigation";

export default function Protected({ roles, children }: { roles?: string[]; children: React.ReactNode }) {
  const { data: me, isLoading } = useMe();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !me) router.push("/login");
    if (!isLoading && me && roles && !roles.some(r => me.roles?.includes(r))) {
      router.push("/"); // or 403 page
    }
  }, [isLoading, me, roles, router]);

  if (isLoading || !me) return null;
  return <>{children}</>;
}

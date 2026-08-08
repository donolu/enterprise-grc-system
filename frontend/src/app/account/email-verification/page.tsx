"use client";

import { Suspense, useEffect, useState } from "react";
import { Alert, Card, Result, Spin, Typography } from "antd";
import { useSearchParams } from "next/navigation";
import { confirmTenantEmailVerification } from "@/lib/services/tenantEmailService";
import { getErrorMessage } from "@/lib/api";

function Confirmation() {
  const searchParams = useSearchParams();
  const token = searchParams.get("token");
  const [state, setState] = useState<"loading" | "success" | "error">("loading");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!token) {
      setState("error");
      setError("This verification link is missing its token.");
      return;
    }

    void confirmTenantEmailVerification(token)
      .then(() => setState("success"))
      .catch((requestError: unknown) => {
        setState("error");
        setError(getErrorMessage(requestError));
      });
  }, [token]);

  if (state === "loading") {
    return <Spin size="large" />;
  }

  if (state === "error") {
    return <Alert type="error" showIcon message="Verification failed" description={error} />;
  }

  return (
    <Result
      status="success"
      title="Sender email verified"
      subTitle="Your tenant email identity is now ready for use."
    />
  );
}

export default function EmailVerificationPage() {
  return (
    <Card style={{ maxWidth: 640, margin: "48px auto" }}>
      <Typography.Title level={3}>Confirm sender email</Typography.Title>
      <Typography.Paragraph type="secondary">
        Confirming the email address configured for your tenant.
      </Typography.Paragraph>
      <Suspense fallback={<Spin size="large" />}>
        <Confirmation />
      </Suspense>
    </Card>
  );
}

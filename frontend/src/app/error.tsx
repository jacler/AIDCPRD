"use client";

import { useEffect } from "react";

import { Button } from "@/components/ui/button";

export default function GlobalError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}) {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-background px-6 text-center">
      <h1 className="text-lg font-semibold">页面加载失败</h1>
      <p className="max-w-md text-sm text-muted-foreground">
        {error.message || "发生未知错误，请刷新页面重试。"}
      </p>
      <div className="flex gap-2">
        <Button onClick={() => reset()}>重试</Button>
        <Button variant="outline" onClick={() => window.location.assign("/")}>
          返回首页
        </Button>
      </div>
    </div>
  );
}

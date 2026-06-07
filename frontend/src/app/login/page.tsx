"use client";

import { Suspense, FormEvent, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { Hexagon, Loader2 } from "lucide-react";

import { register } from "@/lib/api/auth";
import { useAuth } from "@/components/providers/auth-provider";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

function LoginForm() {
  const { login } = useAuth();
  const router = useRouter();
  const searchParams = useSearchParams();
  const redirect = searchParams.get("redirect") ?? "/";

  const [mode, setMode] = useState<"login" | "register">("login");
  const [email, setEmail] = useState("admin@example.com");
  const [password, setPassword] = useState("admin123");
  const [displayName, setDisplayName] = useState("");
  const [error, setError] = useState("");
  const [submitting, setSubmitting] = useState(false);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    setSubmitting(true);
    try {
      if (mode === "login") {
        await login(email, password);
        router.replace(redirect);
      } else {
        await register({ email, password, display_name: displayName });
        await login(email, password);
        router.replace(redirect);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "操作失败");
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <Card className="w-full max-w-md border-slate-800 bg-slate-900/80 text-slate-100 shadow-2xl backdrop-blur">
      <CardHeader className="space-y-3 text-center">
        <div className="mx-auto flex items-center gap-2 text-primary">
          <Hexagon className="h-8 w-8 fill-primary" />
          <span className="text-xl font-bold tracking-tight">AIDC-CostPro</span>
        </div>
        <CardTitle>{mode === "login" ? "登录" : "注册账号"}</CardTitle>
        <CardDescription className="text-slate-400">
          {mode === "login" ? "智算数据中心成本拆解平台" : "注册后可管理项目与 SKU 库"}
        </CardDescription>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-4">
          {mode === "register" && (
            <div className="space-y-2">
              <Label htmlFor="displayName">显示名称</Label>
              <Input
                id="displayName"
                value={displayName}
                onChange={(e) => setDisplayName(e.target.value)}
                required
                className="border-slate-700 bg-slate-800"
              />
            </div>
          )}
          <div className="space-y-2">
            <Label htmlFor="email">邮箱</Label>
            <Input
              id="email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="border-slate-700 bg-slate-800"
            />
          </div>
          <div className="space-y-2">
            <Label htmlFor="password">密码</Label>
            <Input
              id="password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              minLength={6}
              className="border-slate-700 bg-slate-800"
            />
          </div>
          {error && <p className="text-sm text-red-400">{error}</p>}
          <Button type="submit" className="w-full" disabled={submitting}>
            {submitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
            {mode === "login" ? "登录" : "注册并登录"}
          </Button>
        </form>
        <div className="mt-4 text-center text-sm text-slate-400">
          {mode === "login" ? (
            <>
              还没有账号？{" "}
              <button type="button" className="text-primary hover:underline" onClick={() => setMode("register")}>
                立即注册
              </button>
            </>
          ) : (
            <>
              已有账号？{" "}
              <button type="button" className="text-primary hover:underline" onClick={() => setMode("login")}>
                返回登录
              </button>
            </>
          )}
        </div>
        {mode === "login" && (
          <p className="mt-4 rounded-md border border-slate-700 bg-slate-800/50 p-3 text-xs text-slate-400">
            默认管理员：<span className="text-slate-200">admin@example.com</span> /{" "}
            <span className="text-slate-200">admin123</span>
          </p>
        )}
      </CardContent>
    </Card>
  );
}

export default function LoginPage() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-gradient-to-br from-slate-950 via-slate-900 to-slate-950 px-4">
      <Suspense
        fallback={
          <div className="h-8 w-8 animate-spin rounded-full border-2 border-primary border-t-transparent" />
        }
      >
        <LoginForm />
      </Suspense>
    </div>
  );
}

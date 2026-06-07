"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  ChevronDown,
  Hexagon,
  LayoutDashboard,
  LogOut,
  Package,
  Plus,
  Settings,
  Users,
  type LucideIcon,
} from "lucide-react";
import { useState } from "react";

import { useAuth } from "@/components/providers/auth-provider";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

const NAV_ITEMS: { href: string; label: string; icon: LucideIcon; adminOnly?: boolean }[] = [
  { href: "/", label: "仪表盘", icon: LayoutDashboard },
  { href: "/catalog", label: "SKU 库", icon: Package },
  { href: "/users", label: "用户管理", icon: Users, adminOnly: true },
  { href: "/settings", label: "设置", icon: Settings },
];

export function MainNav({ showNewProject = true }: { showNewProject?: boolean }) {
  const pathname = usePathname();
  const router = useRouter();
  const { user, logout } = useAuth();
  const [menuOpen, setMenuOpen] = useState(false);

  const initials = user?.display_name?.slice(0, 1) ?? "?";

  return (
    <header className="sticky top-0 z-50 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <div className="mx-auto flex h-14 max-w-[1440px] items-center justify-between px-6">
        <div className="flex items-center gap-8">
          <Link href="/" className="flex items-center gap-2 font-semibold tracking-tight">
            <Hexagon className="h-6 w-6 fill-primary text-primary" />
            <span>AIDC-CostPro</span>
          </Link>
          <nav className="hidden items-center gap-1 md:flex">
            {NAV_ITEMS.filter((item) => !item.adminOnly || user?.role === "ADMIN").map(
              (item) => {
                const active =
                  item.href === "/"
                    ? pathname === "/"
                    : pathname.startsWith(item.href);
                const Icon = item.icon;
                return (
                  <Link
                    key={item.href}
                    href={item.href}
                    className={cn(
                      "relative flex items-center gap-1.5 rounded-md px-3 py-2 text-sm font-medium transition-colors",
                      active
                        ? "text-primary"
                        : "text-muted-foreground hover:bg-muted hover:text-foreground"
                    )}
                  >
                    <Icon className="h-4 w-4" />
                    {item.label}
                    {active && (
                      <span className="absolute inset-x-2 -bottom-[13px] h-0.5 rounded-full bg-primary" />
                    )}
                  </Link>
                );
              }
            )}
          </nav>
        </div>

        <div className="flex items-center gap-3">
          {showNewProject && (
            <Button size="sm" asChild>
              <Link href="/projects/new">
                <Plus className="h-4 w-4" />
                新建项目
              </Link>
            </Button>
          )}
          <div className="relative">
            <button
              type="button"
              onClick={() => setMenuOpen((o) => !o)}
              className="flex items-center gap-2 rounded-full border px-2 py-1 text-sm transition-colors hover:bg-muted"
            >
              <span className="flex h-7 w-7 items-center justify-center rounded-full bg-primary text-xs font-medium text-primary-foreground">
                {initials}
              </span>
              <span className="hidden sm:inline">{user?.display_name ?? "用户"}</span>
              <ChevronDown className="h-4 w-4 text-muted-foreground" />
            </button>
            {menuOpen && (
              <>
                <div className="fixed inset-0 z-40" onClick={() => setMenuOpen(false)} />
                <div className="absolute right-0 z-50 mt-2 w-48 rounded-lg border bg-card py-1 shadow-lg">
                  <div className="border-b px-3 py-2 text-xs text-muted-foreground">
                    {user?.email}
                    {user?.role === "ADMIN" && (
                      <span className="ml-1 rounded bg-primary/10 px-1 text-primary">管理员</span>
                    )}
                  </div>
                  <button
                    type="button"
                    className="flex w-full items-center gap-2 px-3 py-2 text-sm hover:bg-muted"
                    onClick={() => {
                      setMenuOpen(false);
                      router.push("/settings");
                    }}
                  >
                    <Settings className="h-4 w-4" />
                    账号设置
                  </button>
                  <button
                    type="button"
                    className="flex w-full items-center gap-2 px-3 py-2 text-sm text-destructive hover:bg-muted"
                    onClick={() => {
                      setMenuOpen(false);
                      logout();
                    }}
                  >
                    <LogOut className="h-4 w-4" />
                    退出登录
                  </button>
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </header>
  );
}

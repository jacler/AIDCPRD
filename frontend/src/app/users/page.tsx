"use client";

import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Loader2, Shield, Users } from "lucide-react";

import { useAuth } from "@/components/providers/auth-provider";
import { MainNav } from "@/components/layout/main-nav";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { listUsers, updateUser } from "@/lib/api/auth";
import { useRouter } from "next/navigation";

export default function UsersPage() {
  const { user } = useAuth();
  const router = useRouter();
  const queryClient = useQueryClient();

  const { data, isLoading, error } = useQuery({
    queryKey: ["users"],
    queryFn: () => listUsers(1, 50),
    enabled: user?.role === "ADMIN",
  });

  const toggleMutation = useMutation({
    mutationFn: ({ id, is_active }: { id: string; is_active: boolean }) =>
      updateUser(id, { is_active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["users"] }),
  });

  if (user?.role !== "ADMIN") {
    router.replace("/");
    return null;
  }

  return (
    <div className="min-h-screen bg-gradient-to-b from-slate-50 to-background">
      <MainNav showNewProject />

      <div className="mx-auto max-w-[1000px] px-6 py-8">
        <div className="mb-6">
          <div className="mb-1 flex items-center gap-2 text-primary">
            <Users className="h-5 w-5" />
            <span className="text-sm font-medium">系统管理</span>
          </div>
          <h1 className="text-2xl font-bold">用户管理</h1>
          <p className="mt-1 text-muted-foreground">管理员可查看账号状态并启用/禁用用户</p>
        </div>

        {isLoading ? (
          <div className="flex justify-center py-20">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : error ? (
          <p className="text-sm text-destructive">加载失败</p>
        ) : (
          <div className="overflow-hidden rounded-xl border bg-card shadow-sm">
            <Table>
              <TableHeader>
                <TableRow className="bg-muted/50 hover:bg-muted/50">
                  <TableHead>姓名</TableHead>
                  <TableHead>邮箱</TableHead>
                  <TableHead>角色</TableHead>
                  <TableHead>状态</TableHead>
                  <TableHead>操作</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {(data?.items ?? []).map((u) => (
                  <TableRow key={u.id}>
                    <TableCell className="font-medium">{u.display_name}</TableCell>
                    <TableCell>{u.email}</TableCell>
                    <TableCell>
                      <Badge variant={u.role === "ADMIN" ? "default" : "secondary"}>
                        {u.role === "ADMIN" ? "管理员" : "普通用户"}
                      </Badge>
                    </TableCell>
                    <TableCell>
                      {u.is_active ? (
                        <span className="text-green-600">正常</span>
                      ) : (
                        <span className="text-muted-foreground">已禁用</span>
                      )}
                    </TableCell>
                    <TableCell>
                      {u.id !== user.id && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() =>
                            toggleMutation.mutate({ id: u.id, is_active: !u.is_active })
                          }
                        >
                          {u.is_active ? "禁用" : "启用"}
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
        )}

        <div className="mt-6 flex items-start gap-2 rounded-lg border bg-muted/30 p-4 text-sm text-muted-foreground">
          <Shield className="mt-0.5 h-4 w-4 shrink-0" />
          <p>新用户可通过登录页自助注册。如需创建管理员账号，请使用 API 或联系系统管理员。</p>
        </div>
      </div>
    </div>
  );
}

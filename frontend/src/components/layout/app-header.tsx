import Link from "next/link";
import { Server } from "lucide-react";

interface AppHeaderProps {
  title?: string;
  actions?: React.ReactNode;
}

export function AppHeader({ title, actions }: AppHeaderProps) {
  return (
    <header className="border-b bg-background">
      <div className="flex h-14 items-center justify-between px-4">
        <div className="flex items-center gap-4">
          <Link href="/" className="flex items-center gap-2 hover:opacity-80">
            <Server className="h-5 w-5 text-primary" />
            <span className="font-semibold">AIDC-CostPro</span>
          </Link>
          {title && (
            <>
              <span className="text-muted-foreground">/</span>
              <span className="text-sm text-muted-foreground">{title}</span>
            </>
          )}
        </div>
        {actions}
      </div>
    </header>
  );
}

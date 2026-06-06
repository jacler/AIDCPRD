import { DesignerWorkspace } from "@/components/designer/designer-workspace";

interface PageProps {
  params: { id: string };
}

export default function DesignerPage({ params }: PageProps) {
  return <DesignerWorkspace projectId={params.id} />;
}

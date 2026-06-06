import { ComparePageClient } from "@/components/compare/compare-page-client";

interface PageProps {
  params: { id: string };
}

export default function ComparePage({ params }: PageProps) {
  return <ComparePageClient projectId={params.id} />;
}

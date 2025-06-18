import { Badge } from "@/components/ui/badge"

interface TaskStatusBadgeProps {
  status: string
}

export function TaskStatusBadge({ status }: TaskStatusBadgeProps) {
  const getVariant = (status: string) => {
    switch (status?.toLowerCase()) {
      case "completed":
        return "default"
      case "running":
        return "secondary" 
      case "failed":
        return "destructive"
      default:
        return "outline"
    }
  }

  return (
    <Badge variant={getVariant(status)}>
      {status}
    </Badge>
  )
}
